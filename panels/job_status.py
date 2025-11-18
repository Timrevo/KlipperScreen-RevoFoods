# -*- coding: utf-8 -*-
from ks_includes.KlippyGtk import find_widget
from ks_includes.screen_panel import ScreenPanel
from time import time
from statistics import median
from math import pi, sqrt, trunc
from gi.repository import GLib, Gtk, Pango
import logging
import os
import json
from datetime import datetime

import gi

gi.require_version("Gtk", "3.0")


class Panel(ScreenPanel):
    # Class variable to store temporary rates per product during session
    _temp_rates = {}

    def __init__(self, screen, title):
        title = title or _("Job Status")
        super().__init__(screen, title)

        self.product_extrusion_rates = {}

        try:
            self._load_product_defaults()
        except Exception:
            pass

        self.thumb_dialog = None
        self.grid = Gtk.Grid(column_homogeneous=True)
        self.pos_z = 0.0
        self.extrusion = 100
        self.speed_factor = 1.0
        self.speed = 100
        self.req_speed = 0
        self.oheight = 0.0
        self.current_extruder = None
        self.fila_section = pi * ((1.75 / 2) ** 2)
        self.filename_label = {'complete': "Filename"}
        self.filename = ""
        self.prev_pos = None
        self.prev_gpos = None
        self.can_close = False
        self.flow_timeout = None
        self.animation_timeout = None
        self.file_metadata = self.fans = {}
        self.state = "standby"
        self.timeleft_type = "auto"
        self.progress = 0.0
        self.zoffset = 0.0
        self.flowrate = 0.0
        self.vel = 0.0
        self.flowstore = []
        self.mm = _("mm")
        self.mms = _("mm/s")
        self.mms2 = _("mm/s²")
        self.mms3 = _("mm³/s")
        self.status_grid = None
        self.move_grid = None
        self.time_grid = None

        data = ['pos_x', 'pos_y', 'pos_z', 'time_left', 'duration', 'slicer_time', 'file_time',
                'filament_time', 'est_time', 'speed_factor', 'req_speed', 'max_accel', 'extrude_factor', 'zoffset',
                'zoffset', 'filament_used', 'filament_total', 'advance', 'layer', 'total_layers', 'height',
                'flowrate']

        for item in data:
            self.labels[item] = Gtk.Label(label="-", hexpand=True, vexpand=True)

        self.labels['left'] = Gtk.Label(_("Left:"))
        self.labels['elapsed'] = Gtk.Label(_("Elapsed:"))
        self.labels['total'] = Gtk.Label(_("Total:"))
        self.labels['slicer'] = Gtk.Label(_("Slicer:"))
        self.labels['file_tlbl'] = Gtk.Label(_("File:"))
        self.labels['fila_tlbl'] = Gtk.Label(_("Filament:"))
        self.labels['speed_lbl'] = Gtk.Label(_("Speed:"))
        self.labels['accel_lbl'] = Gtk.Label(_("Acceleration:"))
        self.labels['flow'] = Gtk.Label(_("Flow:"))
        self.labels['zoffset_lbl'] = Gtk.Label(_("Z offset:"))
        self.labels['fila_used_lbl'] = Gtk.Label(_("Filament used:"))
        self.labels['fila_total_lbl'] = Gtk.Label(_("Filament total:"))
        self.labels['pa_lbl'] = Gtk.Label(_("Pressure Advance:"))
        self.labels['flowrate_lbl'] = Gtk.Label(_("Flowrate:"))
        self.labels['height_lbl'] = Gtk.Label(_("Height:"))
        self.labels['layer_lbl'] = Gtk.Label(_("Layer:"))


        for fan in self._printer.get_fans():
            # fan_types = ["controller_fan", "fan_generic", "heater_fan"]
            if fan == "fan":
                name = " "
            elif fan.startswith("fan_generic"):
                name = " ".join(fan.split(" ")[1:])[:1].upper() + ":"
                if name.startswith("_"):
                    continue
            else:
                continue
            self.fans[fan] = {
                "name": name,
                "speed": "-"
            }

        self.labels['file'] = Gtk.Label(label="Filename", hexpand=True)
        self.labels['file'].get_style_context().add_class("printing-filename")
        self.labels['file'].set_halign(Gtk.Align.CENTER)  # Center the filename
        self.labels['lcdmessage'] = Gtk.Label(no_show_all=True)
        self.labels['lcdmessage'].get_style_context().add_class("printing-status")
        self.labels['lcdmessage'].set_halign(Gtk.Align.CENTER)  # Center the LCD message too

        for label in self.labels:
            if label not in ['file', 'lcdmessage']:  # Skip filename and LCD message
                self.labels[label].set_halign(Gtk.Align.START)
            self.labels[label].set_ellipsize(Pango.EllipsizeMode.END)

        fi_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, valign=Gtk.Align.CENTER)
        fi_box.add(self.labels['file'])
        fi_box.add(self.labels['lcdmessage'])
        self.grid.attach(fi_box, 0, 0, 4, 1)

        # Add file icon above the progress circle
        self.labels['file_icon'] = self._gtk.Image("file", self._gtk.font_size * 12)
        icon_box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        icon_box.add(self.labels['file_icon'])
        self.grid.attach(icon_box, 0, 1, 4, 1)

        # Create a large progress circle in the center
        self.labels['darea'] = Gtk.DrawingArea()
        self.labels['darea'].connect("draw", self.on_draw)

        box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.labels['progress_text'] = Gtk.Label(label="0%")
        self.labels['progress_text'].get_style_context().add_class("printing-progress-text")
        box.add(self.labels['progress_text'])

        overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        overlay.set_size_request(*(self._gtk.font_size * 15,) * 2)  # Make it larger
        overlay.add(self.labels['darea'])
        overlay.add_overlay(box)
        # Position the progress circle above the buttons
        self.grid.attach(overlay, 0, 3, 4, 1)

        self.current_extruder = self._printer.get_stat("toolhead", "extruder")
        if self.current_extruder:
            diameter = float(self._printer.get_config_section(self.current_extruder)['filament_diameter'])
            self.fila_section = pi * ((diameter / 2) ** 2)

        self.buttons = {}
        self.create_buttons()
        self.buttons['button_grid'] = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, vexpand=False)
        self.grid.attach(self.buttons['button_grid'], 0, 4, 4, 1)  # Move down to accommodate icon

        # Remove creation of info grids since we don't need them anymore
        self.content.add(self.grid)

        # Helper class for custom spin inputs with - and + buttons
        class CustomSpinBox(Gtk.Box):
            def __init__(self, min_val, max_val, step, initial_val, callback):
                super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

                # Minus button on the left
                self.minus_btn = Gtk.Button(label="-")
                self.minus_btn.get_style_context().add_class("action-btn")
                self.pack_start(self.minus_btn, False, False, 0)

                # Entry in the middle
                self.entry = Gtk.Entry()
                self.entry.set_text(str(initial_val))
                self.entry.set_width_chars(4)
                self.entry.set_max_width_chars(4)
                self.entry.set_alignment(0.5)  # Center text
                self.pack_start(self.entry, True, True, 0)

                # Plus button on the right
                self.plus_btn = Gtk.Button(label="+")
                self.plus_btn.get_style_context().add_class("action-btn")
                self.pack_start(self.plus_btn, False, False, 0)

                self.min_val = min_val
                self.max_val = max_val
                self.step = step
                self.callback = callback

                def on_plus_clicked(button):
                    try:
                        val = float(self.entry.get_text())
                        val = min(self.max_val, val + self.step)
                        self.set_value(val)
                    except ValueError:
                        self.set_value(initial_val)

                def on_minus_clicked(button):
                    try:
                        val = float(self.entry.get_text())
                        val = max(self.min_val, val - self.step)
                        self.set_value(val)
                    except ValueError:
                        self.set_value(initial_val)

                def on_entry_changed(entry):
                    try:
                        val = float(entry.get_text())
                        val = max(self.min_val, min(self.max_val, val))
                        self.set_value(val)
                    except ValueError:
                        self.set_value(initial_val)

                self.minus_btn.connect("clicked", on_minus_clicked)
                self.plus_btn.connect("clicked", on_plus_clicked)
                self.entry.connect("activate", lambda e: on_entry_changed(e))

            def set_value(self, value):
                self.entry.set_text(str(int(value)))
                self.callback(value)

            def get_value(self):
                try:
                    return float(self.entry.get_text())
                except ValueError:
                    return 0.0

            def get_value_as_int(self):
                try:
                    return int(float(self.entry.get_text()))
                except ValueError:
                    return 0

        # Create custom inputs with JSON defaults (product-specific will be set in update_filename)
        try:
            data = self._read_rates_file()
            orange_default = data['orange']
            white_default = data['white']
        except Exception as e:
            logging.debug(f"No saved extrusion rates found; using defaults: {e}")
            orange_default = 100
            white_default = 100
        self.orange_input = CustomSpinBox(10, 150, 2, orange_default, self.on_orange_rate_changed)
        self.white_input = CustomSpinBox(10, 200, 10, white_default, self.on_white_rate_changed)

        # Create input controls for extrusion rates
        orange_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, halign=Gtk.Align.CENTER)
        orange_label = Gtk.Label(label=_("Orange extrusion rate"))
        orange_label.get_style_context().add_class("orange-label")
        orange_box.add(orange_label)
        orange_range_label = Gtk.Label(label=_("Range: [10-150]"))
        orange_range_label.get_style_context().add_class("dim-label")
        orange_box.add(orange_range_label)
        orange_box.add(self.orange_input)

        white_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, halign=Gtk.Align.CENTER)
        white_label = Gtk.Label(label=_("White extrusion rate"))
        white_box.add(white_label)
        white_range_label = Gtk.Label(label=_("Range: [10-200]"))
        white_range_label.get_style_context().add_class("dim-label")
        white_box.add(white_range_label)
        white_box.add(self.white_input)

    # Add extruder controls to grid with increased spacing between inputs
        self.extruder_box = Gtk.Box(spacing=120, halign=Gtk.Align.CENTER)
        self.extruder_box.add(orange_box)
        self.extruder_box.add(white_box)
        extruder_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, halign=Gtk.Align.CENTER)
        extruder_container.add(self.extruder_box)
        save_btn_box = Gtk.Box(halign=Gtk.Align.CENTER)
        self.save_rates_button = Gtk.Button(label=_("Save as default"))
        self.save_rates_button.get_style_context().add_class("save-button")
        self.save_rates_button.connect("clicked", self.on_save_clicked)
        save_btn_box.pack_start(self.save_rates_button, False, False, 0)
        extruder_container.add(save_btn_box)
        self.grid.attach(extruder_container, 0, 2, 4, 1)

    def on_draw(self, da, ctx):
        w = da.get_allocated_width()
        h = da.get_allocated_height()
        r = min(w, h) * .42

        # Background circle with shadow effect
        ctx.set_source_rgba(0.05, 0.05, 0.05, 0.8)  # Dark shadow
        ctx.set_line_width(self._gtk.font_size * .9)
        ctx.translate(w / 2, h / 2)
        ctx.arc(0, 0, r + 2, 0, 2 * pi)
        ctx.stroke()

        # Main background circle
        ctx.set_source_rgb(0.15, 0.15, 0.15)  # Lighter dark background
        ctx.set_line_width(self._gtk.font_size * .75)
        ctx.arc(0, 0, r, 0, 2 * pi)
        ctx.stroke()

        # Progress arc with gradient-like effect
        # Inner glow effect
        ctx.set_source_rgba(0.2, 0.6, 1.0, 0.3)  # Blue glow
        ctx.set_line_width(self._gtk.font_size * 1.0)
        ctx.arc(0, 0, r, 3 / 2 * pi, 3 / 2 * pi + (self.progress * 2 * pi))
        ctx.stroke()

        # Main progress arc
        ctx.set_source_rgb(0.2, 0.7, 1.0)  # Beautiful blue
        ctx.set_line_width(self._gtk.font_size * .75)
        ctx.arc(0, 0, r, 3 / 2 * pi, 3 / 2 * pi + (self.progress * 2 * pi))
        ctx.stroke()

        # Outer highlight
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.6)  # White highlight
        ctx.set_line_width(self._gtk.font_size * .2)
        ctx.arc(0, 0, r + self._gtk.font_size * .4, 3 / 2 * pi, 3 / 2 * pi + (self.progress * 2 * pi))
        ctx.stroke()

    def save_current_rates(self):
        """Save current extrusion rates to config file.

        Behavior:
        - Persist both top-level fallback values and a per-product entry.
        - Clear the temporary session rates after a successful save.
        """
        current_rates = {
            'orange': self.orange_input.get_value_as_int(),
            'white': self.white_input.get_value_as_int()
        }
        try:
            data = self._read_rates_file()
            data['orange'] = current_rates['orange']
            data['white'] = current_rates['white']

            # also store per-product values under product key
            product_key = self._get_product_key()
            if product_key:
                data[product_key] = {
                    'orange': current_rates['orange'],
                    'white': current_rates['white']
                }

            success = self._write_rates_file(data)

            if success:
                # Clear temporary session rates as they've been persisted
                Panel._temp_rates.clear()
                self._session_rates_changed = False
                # Show confirmation popup to the user
                try:
                    GLib.idle_add(self._screen.show_popup_message, _("Changes saved successfully!"), 1)
                except Exception:
                    pass
                logging.info(f"Saved extrusion rates: Orange={current_rates['orange']}%, White={current_rates['white']}% (product={product_key})")
            else:
                logging.error("Failed to save extrusion rates file")
        except Exception as e:
            logging.error(f"Error saving extrusion rates: {e}")

    def on_save_clicked(self, widget):
        """Handler for Save button click: show pressed visual and persist rates."""
        ctx = widget.get_style_context()
        try:
            # add the visual class
            ctx.add_class('save-clicked')
        except Exception:
            pass

        try:
            self.save_current_rates()
        finally:
            def _remove_class():
                try:
                    ctx.remove_class('save-clicked')
                except Exception:
                    pass
                return False

            GLib.timeout_add(600, _remove_class)

    def _rates_file_path(self):
        return os.path.join(os.path.dirname(__file__), '..', 'config', 'extrusion_rates.json')

    def _read_rates_file(self):
        path = self._rates_file_path()
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f) or {}
        except Exception:
            logging.debug("Failed to read extrusion rates file; proceeding with empty data")
        return {}

    def _write_rates_file(self, data):
        path = self._rates_file_path()
        try:
            # ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Failed writing extrusion rates file: {e}")
            return False

    def load_saved_rates(self):
        """Load saved extrusion rates and apply them for the current product.

        Does not overwrite any temporary session values in Panel._temp_rates.
        """
        data = self._read_rates_file()
        product_key = self._get_product_key()

        # Prefer per-product saved values
        if product_key and isinstance(data.get(product_key), dict):
            rates = data[product_key]
            # don't overwrite if user has a temp value for this product
            temp = Panel._temp_rates.get(product_key, {})
            if 'orange' not in temp and 'orange' in rates:
                self.orange_input.set_value(rates.get('orange'))
            if 'white' not in temp and 'white' in rates:
                self.white_input.set_value(rates.get('white'))
            logging.info(f"Loaded per-product saved rates for {product_key}: {rates}")
            return

        # Fall back to top-level values
        if 'orange' in data and 'white' in data:
            temp_global = Panel._temp_rates.get(product_key, {})
            if 'orange' not in temp_global:
                self.orange_input.set_value(data.get('orange'))
            if 'white' not in temp_global:
                self.white_input.set_value(data.get('white'))
            logging.info(f"Loaded global saved extrusion rates: orange={data.get('orange')}, white={data.get('white')}")

    def on_orange_rate_changed(self, value):
        new_rate = int(value)

        # Check if printer is actively printing
        is_printing = self.state in ["printing", "paused"]

        if is_printing:
            # During printing: Only use direct commands (no T0 macro due to MOVE=1)
            try:
                # Update your macro variables for consistency
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=curr_ospeed VALUE={new_rate}")
                # Apply directly without movement
                self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder")
                self._screen._ws.klippy.gcode_script(f"M221 S{new_rate}")
                logging.info(f"ORANGE: Set to {new_rate}% via direct M221 (printing mode)")
            except Exception as e:
                logging.error(f" ORANGE: Failed to set rate during printing: {e}")
        else:
            # When not printing: Use your macro system properly
            try:
                # Update both current and initial values in your macro system
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=curr_ospeed VALUE={new_rate}")
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=ini_ospeed VALUE={new_rate}")
                # Use T0 macro (with movement allowed when not printing)
                self._screen._ws.klippy.gcode_script("T0")
                logging.info(f"ORANGE: Set to {new_rate}% via T0 macro system")
            except Exception as e:
                # Fallback: Direct commands
                try:
                    self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder")
                    self._screen._ws.klippy.gcode_script(f"M221 S{new_rate}")
                    logging.info(f"ORANGE: Set to {new_rate}% via direct method")
                except Exception as e2:
                    logging.error(f"ORANGE: All methods failed: {e2}")


        # Store per-product temporary rates for the session and mark as changed
        product_key = self._get_product_key()
        if product_key:
            Panel._temp_rates.setdefault(product_key, {})
            Panel._temp_rates[product_key]['orange'] = new_rate
        self._session_rates_changed = True

    def on_white_rate_changed(self, value):
        new_rate = int(value)

        # Check if printer is actively printing
        is_printing = self.state in ["printing", "paused"]

        if is_printing:
            # During printing: Only use direct commands (no T1 macro due to MOVE=1)
            try:
                # Update your macro variables for consistency
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=curr_wspeed VALUE={new_rate}")
                # Apply directly without movement
                self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder1")
                self._screen._ws.klippy.gcode_script(f"M221 S{new_rate}")
                logging.info(f" WHITE: Set to {new_rate}% via direct M221 (printing mode)")
            except Exception as e:
                logging.error(f" WHITE: Failed to set rate during printing: {e}")
        else:
            # When not printing: Use your macro system properly
            try:
                # Update both current and initial values in your macro system
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=curr_wspeed VALUE={new_rate}")
                self._screen._ws.klippy.gcode_script(f"SET_GCODE_VARIABLE MACRO=_exvar VARIABLE=ini_wspeed VALUE={new_rate}")
                # Use T1 macro (with movement allowed when not printing)
                self._screen._ws.klippy.gcode_script("T1")
                logging.info(f" WHITE: Set to {new_rate}% via T1 macro system")
            except Exception as e:
                # Fallback: Direct commands
                try:
                    self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder1")
                    self._screen._ws.klippy.gcode_script(f"M221 S{new_rate}")
                    logging.info(f" WHITE: Set to {new_rate}% via direct method")
                except Exception as e2:
                    logging.error(f" WHITE: All methods failed: {e2}")



        # Store per-product temporary rates for the session and mark as changed
        product_key = self._get_product_key()
        if product_key:
            Panel._temp_rates.setdefault(product_key, {})
            Panel._temp_rates[product_key]['white'] = new_rate
        self._session_rates_changed = True

    def apply_extrusion_rate(self, product, extruder):
        rate = self.product_extrusion_rates[product][extruder]
        if extruder == "Orange":
            self.orange_input.set_value(rate)
        elif extruder == "White":
            self.white_input.set_value(rate)

    def activate(self):
        if self.flow_timeout is None:
            self.flow_timeout = GLib.timeout_add_seconds(2, self.update_flow)
        if self.animation_timeout is None:
            self.animation_timeout = GLib.timeout_add(500, self.animate_label)

        # Force apply current default extrusion rates to printer when panel activates
        self.force_apply_default_rates()

    def force_apply_default_rates(self):
        """Force the printer to use the current default extrusion rates"""
        try:
            # First, ensure we load the latest JSON values
            self.load_saved_rates()

            orange_rate = self.orange_input.get_value_as_int()
            white_rate = self.white_input.get_value_as_int()

            # Apply Orange rate
            self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder")
            self._screen._ws.klippy.gcode_script(f"M221 S{orange_rate}")

            # Apply White rate
            self._screen._ws.klippy.gcode_script("ACTIVATE_EXTRUDER EXTRUDER=extruder1")
            self._screen._ws.klippy.gcode_script(f"M221 S{white_rate}")
        except Exception as e:
            logging.error(f"Failed to force apply default rates: {e}")

    def deactivate(self):
        if self.flow_timeout is not None:
            self.record_print_start_time()
            GLib.source_remove(self.flow_timeout)
            self.flow_timeout = None
        if self.animation_timeout is not None:
            GLib.source_remove(self.animation_timeout)
            self.animation_timeout = None

    def create_buttons(self):

        self.buttons = {
            'cancel': self._gtk.Button("stop", _("Cancel"), "red"),
            'control': self._gtk.Button("settings", _("Settings"), "blue_move"),
            'fine_tune': self._gtk.Button("fine-tune", _("Fine Tuning"), "blue_move"),
            'menu': self._gtk.Button("complete", _("Main Menu"), "green"),
            'pause': self._gtk.Button("pause", _("Pause"), "setting_move"),
            'restart': self._gtk.Button("refresh", _("Restart"), "blue_move"),
            'resume': self._gtk.Button("resume", _("Resume"), "arrows"),
            'save_offset_probe': self._gtk.Button("home-z", _("Save Z") + "\n" + "Probe", "setting_move"),
            'save_offset_endstop': self._gtk.Button("home-z", _("Save Z") + "\n" + "Endstop", "setting_move"),
        }

        # Create quality selection buttons (0-8) for completed state
        self.quality_buttons = {}
        for i in range(9):
            self.quality_buttons[f'quality_{i}'] = self._gtk.Button("complete", str(i), "green")
            self.quality_buttons[f'quality_{i}'].connect("clicked", self.quality_selected, i)

        # Create last print checkbox
        self.last_print_checkbox = Gtk.CheckButton(label=_("Last print"))
        self.last_print_checkbox.set_halign(Gtk.Align.CENTER)
        self.buttons['cancel'].connect("clicked", self.cancel)
        self.buttons['control'].connect("clicked", self._screen._go_to_submenu, "")
        self.buttons['fine_tune'].connect("clicked", self.menu_item_clicked, {
            "panel": "fine_tune"})
        self.buttons['menu'].connect("clicked", self.close_panel)
        self.buttons['pause'].connect("clicked", self.pause)
        self.buttons['restart'].connect("clicked", self.restart)
        self.buttons['resume'].connect("clicked", self.resume)
        self.buttons['save_offset_probe'].connect("clicked", self.save_offset, "probe")
        self.buttons['save_offset_endstop'].connect("clicked", self.save_offset, "endstop")

    def quality_selected(self, widget, quality_count):
        """Handle quality selection (1-8 good prints)"""
        is_last_print = self.last_print_checkbox.get_active()
        good_prints = quality_count
        bad_prints = 8 - quality_count

        # Save to history
        self.save_quality_history(good_prints, bad_prints)

        if is_last_print:
            # Go back to main menu
            logging.info(f"Last print selected, returning to main menu")
            self.can_close = True  # Enable closing
            self.close_panel()
        else:
            # Restart the print
            if self.filename:
                logging.info(f"Restarting print after quality selection: {self.filename}")
                if self.state == "error":
                    self._screen._ws.klippy.gcode_script("SDCARD_RESET_FILE")
                self._screen._ws.klippy.print_start(self.filename)
                self.record_print_start_time()
                self.new_print()
            else:
                logging.info(f"Could not restart {self.filename}")

    def save_quality_history(self, good_prints, bad_prints):
        """Save quality history with good and bad print counts"""
        if not self.filename:
            return

        history_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'history.json')
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            # Read existing history
            if os.path.exists(history_file) and os.path.getsize(history_file) > 0:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
            else:
                history_data = {}

            # Check if it's the first entry for today (new date)
            is_new_day = today not in history_data

            # Initialize date entry if it doesn't exist
            if is_new_day:
                history_data[today] = {}
                # Clean old entries (more than 30 days) when adding a new date
                self.clean_old_history_entries(history_data, today)

            # Initialize filename entry if it doesn't exist
            if self.filename not in history_data[today]:
                history_data[today][self.filename] = {"good": 0, "bad": 0}

            # Add the new counts
            history_data[today][self.filename]["good"] += good_prints
            history_data[today][self.filename]["bad"] += bad_prints

            # Save the updated history
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            logging.info(f"Quality history saved: {self.filename} - {today} - Good: {good_prints}, Bad: {bad_prints}")

        except Exception as e:
            logging.error(f"Error while saving quality history: {e}")

    def _load_product_defaults(self):
        cfg = self._read_rates_file()
        for key, val in list(cfg.items()):
            if isinstance(val, dict):
                self.product_extrusion_rates.setdefault(key, {})
                # Keep lowercase keys consistent with your JSON file
                if 'orange' in val:
                    self.product_extrusion_rates[key]['orange'] = val['orange']
                if 'white' in val:
                    self.product_extrusion_rates[key]['white'] = val['white']

    def clean_old_history_entries(self, history_data, current_date):
        """Clean history entries older than 30 days"""
        try:
            from datetime import datetime, timedelta

            current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            cutoff_date = current_date_obj - timedelta(days=30)

            dates_to_remove = []
            for date_str in history_data.keys():
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if date_obj < cutoff_date:
                        dates_to_remove.append(date_str)
                except ValueError:
                    # Skip invalid date formats
                    logging.warning(f"Invalid date format in history: {date_str}")
                    continue

            if dates_to_remove:
                for old_date in dates_to_remove:
                    del history_data[old_date]
                logging.info(f"Cleaned {len(dates_to_remove)} old history entries older than 30 days: {dates_to_remove}")
            else:
                logging.debug("No old history entries to clean")

        except Exception as e:
            logging.error(f"Error while cleaning old history entries: {e}")

    def save_offset(self, widget, device):
        sign = "+" if self.zoffset > 0 else "-"
        label = Gtk.Label(hexpand=True, vexpand=True, wrap=True)
        saved_z_offset = None
        msg = f"Apply {sign}{abs(self.zoffset)} offset to {device}?"
        if device == "probe":
            msg = _("Apply %s%.3f offset to Probe?") % (sign, abs(self.zoffset))
            if probe := self._printer.get_probe():
                saved_z_offset = probe['z_offset']
        elif device == "endstop":
            msg = _("Apply %s%.3f offset to Endstop?") % (sign, abs(self.zoffset))
            if 'stepper_z' in self._printer.get_config_section_list():
                saved_z_offset = self._printer.get_config_section('stepper_z')['position_endstop']
            elif 'stepper_a' in self._printer.get_config_section_list():
                saved_z_offset = self._printer.get_config_section('stepper_a')['position_endstop']
        if saved_z_offset:
            msg += "\n\n" + _("Saved offset: %s") % saved_z_offset
        label.set_label(msg)
        buttons = [
            {"name": _("Apply"), "response": Gtk.ResponseType.APPLY, "style": 'dialog-default'},
            {"name": _("Cancel"), "response": Gtk.ResponseType.CANCEL, "style": 'dialog-error'}
        ]
        self._gtk.Dialog(_("Save Z"), buttons, label, self.save_confirm, device)

    def save_confirm(self, dialog, response_id, device):
        self._gtk.remove_dialog(dialog)
        if response_id == Gtk.ResponseType.APPLY:
            if device == "probe":
                self._screen._ws.klippy.gcode_script("Z_OFFSET_APPLY_PROBE")
            if device == "endstop":
                self._screen._ws.klippy.gcode_script("Z_OFFSET_APPLY_ENDSTOP")
            self._screen._ws.klippy.gcode_script("SAVE_CONFIG")

    def restart(self, widget):
        if self.filename:
            self.disable_button("restart")
            if self.state == "error":
                self._screen._ws.klippy.gcode_script("SDCARD_RESET_FILE")
            self._screen._ws.klippy.print_start(self.filename)
            logging.info(f"Starting print: {self.filename}")
            self.record_print_start_time()
            self.new_print()
        else:
            logging.info(f"Could not restart {self.filename}")

    def resume(self, widget):
        self._screen._ws.klippy.print_resume()
        self._screen.show_all()

    def pause(self, widget):
        self.disable_button("pause", "resume")
        self._screen._ws.klippy.print_pause()
        self._screen.show_all()

    def cancel(self, widget):
        buttons = [
            {"name": _("Cancel Print"), "response": Gtk.ResponseType.OK, "style": 'dialog-error'},
            {"name": _("Go Back"), "response": Gtk.ResponseType.CANCEL, "style": 'dialog-info'}
        ]
        if len(self._printer.get_stat("exclude_object", "objects")) > 1:
            buttons.insert(0, {"name": _("Exclude Object"), "response": Gtk.ResponseType.APPLY})
        label = Gtk.Label(hexpand=True, vexpand=True, wrap=True)
        label.set_markup(_("Are you sure you wish to cancel this print?"))
        self._gtk.Dialog(_("Cancel"), buttons, label, self.cancel_confirm)

    def cancel_confirm(self, dialog, response_id):
        self._gtk.remove_dialog(dialog)
        if response_id == Gtk.ResponseType.APPLY:
            self.menu_item_clicked(None, {"panel": "exclude"})
            return
        if response_id == Gtk.ResponseType.CANCEL:
            self.enable_button("pause", "cancel")
            return
        logging.debug("Canceling print")
        # Save current rates for this product before canceling
        product_key = self._get_product_key()
        Panel._temp_rates[product_key] = {
            'orange': self.orange_input.get_value_as_int(),
            'white': self.white_input.get_value_as_int()
        }
        self.set_state("cancelling")
        self.disable_button("pause", "resume", "cancel")
        self._screen._ws.klippy.print_cancel()

    def close_panel(self, widget=None):
        if self.can_close:
            logging.debug("Closing job_status panel")
            self._screen.state_ready(wait=False)

    def enable_button(self, *args):
        for arg in args:
            self.buttons[arg].set_sensitive(True)

    def disable_button(self, *args):
        for arg in args:
            self.buttons[arg].set_sensitive(False)

    def new_print(self):
        self._screen.screensaver.close()
        if "virtual_sdcard" in self._printer.data:
            logging.info("reseting progress")
            self._printer.data["virtual_sdcard"]["progress"] = 0
        # Show progress circle and text for new print
        self.labels['darea'].set_visible(True)
        self.labels['progress_text'].set_visible(True)
        self.update_progress(0.0)
        # Reset the last print checkbox for next time
        self.last_print_checkbox.set_active(False)

        # Force apply current extrusion rates at start of new print
        self.force_apply_default_rates()

        self.set_state("printing")

    def process_update(self, action, data):
        if action == "notify_gcode_response":
            if "action:cancel" in data:
                self.set_state("cancelled")
            elif "action:paused" in data:
                self.set_state("paused")
            elif "action:resumed" in data:
                self.set_state("printing")
            return
        elif action == "notify_metadata_update" and data['filename'] == self.filename:
            self.get_file_metadata(response=True)
        elif action != "notify_status_update":
            return

        for x in self._printer.get_temp_devices():
            if x in data:
                self.update_temp(
                    x,
                    self._printer.get_stat(x, "temperature"),
                    self._printer.get_stat(x, "target"),
                    self._printer.get_stat(x, "power"),
                    digits=0
                )

        if "display_status" in data and "message" in data["display_status"]:
            if data['display_status']['message']:
                self.labels['lcdmessage'].set_label(f"{data['display_status']['message']}")
                self.labels['lcdmessage'].show()
            else:
                self.labels['lcdmessage'].hide()

        if 'toolhead' in data:
            if 'extruder' in data['toolhead'] and data['toolhead']['extruder'] != self.current_extruder:
                self.current_extruder = data["toolhead"]["extruder"]
            if "max_accel" in data["toolhead"]:
                self.labels['max_accel'].set_label(f"{data['toolhead']['max_accel']:.0f} {self.mms2}")
        if 'extruder' in data and 'pressure_advance' in data['extruder']:
            self.labels['advance'].set_label(f"{data['extruder']['pressure_advance']:.2f}")

        if 'gcode_move' in data:
            if 'gcode_position' in data['gcode_move']:
                self.pos_z = round(float(data['gcode_move']['gcode_position'][2]), 2)
            if 'extrude_factor' in data['gcode_move']:
                self.extrusion = round(float(data['gcode_move']['extrude_factor']) * 100)
            if 'speed_factor' in data['gcode_move']:
                self.speed = round(float(data['gcode_move']['speed_factor']) * 100)
                self.speed_factor = float(data['gcode_move']['speed_factor'])
            if 'speed' in data['gcode_move']:
                self.req_speed = round(float(data["gcode_move"]["speed"]) / 60 * self.speed_factor)
            if 'homing_origin' in data['gcode_move']:
                self.zoffset = float(data['gcode_move']['homing_origin'][2])
        if 'motion_report' in data:
            if 'live_position' in data['motion_report']:
                pos = data["motion_report"]["live_position"]
                now = time()
                if self.prev_pos is not None:
                    interval = (now - self.prev_pos[1])
                    # Calculate Flowrate
                    evelocity = (pos[3] - self.prev_pos[0][3]) / interval
                    self.flowstore.append(self.fila_section * evelocity)
                self.prev_pos = [pos, now]
            if 'live_velocity' in data['motion_report']:
                self.vel = float(data["motion_report"]["live_velocity"])
            if 'live_extruder_velocity' in data['motion_report']:
                self.flowstore.append(self.fila_section * float(data["motion_report"]["live_extruder_velocity"]))

        # Remove fan processing since we don't display it anymore
        if "print_stats" in data:
            if 'state' in data['print_stats']:
                self.set_state(
                    data["print_stats"]["state"],
                    msg=f'{data["print_stats"]["message"] if "message" in data["print_stats"] else ""}'
                )
            if 'filename' in data['print_stats']:
                self.update_filename(data['print_stats']["filename"])
            if 'filament_used' in data['print_stats']:
                # Keep the data but don't display it in buttons anymore
                pass
            if 'info' in data["print_stats"]:
                # Keep layer info but don't display it
                pass
            if 'total_duration' in data["print_stats"]:
                # Keep duration but don't display it
                pass
            if self.state in ["printing", "paused"]:
                self.update_time_left()

    def update_flow(self):
        if not self.flowstore:
            self.flowstore.append(0)
        self.flowrate = median(self.flowstore)
        self.flowstore = []
        # Remove button updates since we don't have those buttons anymore
        return True

    def update_time_left(self):
        progress = (
            max(self._printer.get_stat('virtual_sdcard', 'file_position') - self.file_metadata['gcode_start_byte'], 0)
            / (self.file_metadata['gcode_end_byte'] - self.file_metadata['gcode_start_byte'])
        ) if "gcode_start_byte" in self.file_metadata else self._printer.get_stat('virtual_sdcard', 'progress')

        # Remove button label updates since we don't have those buttons anymore
        # Just keep the progress calculation
        self.update_progress(progress)

    def estimate_time(self, progress, print_duration, file_time, filament_time, slicer_time, last_time):
        estimate_above = 0.3
        slicer_time /= sqrt(self.speed_factor)
        if progress <= estimate_above:
            return last_time or slicer_time or filament_time or file_time
        objects = self._printer.get_stat("exclude_object", "objects")
        excluded_objects = self._printer.get_stat("exclude_object", "excluded_objects")
        exclude_compensation = 3 * (len(excluded_objects) / len(objects)) if len(objects) > 0 else 0
        weight_last = 4.0 - exclude_compensation if print_duration < last_time else 0
        weight_slicer = 1.0 + estimate_above - progress - exclude_compensation if print_duration < slicer_time else 0
        weight_filament = min(progress - estimate_above, 0.33) if print_duration < filament_time else 0
        weight_file = progress - estimate_above
        total_weight = weight_last + weight_slicer + weight_filament + weight_file
        if total_weight == 0:
            return 0
        return (
            (
                last_time * weight_last
                + slicer_time * weight_slicer
                + filament_time * weight_filament
                + file_time * weight_file
            )
            / total_weight
        )

    def update_progress(self, progress: float):
        self.progress = progress
        self.labels['progress_text'].set_label(f"{trunc(progress * 100)}%")
        self.labels['darea'].queue_draw()

    def set_state(self, state, msg=""):
        if state == "printing":
            self._screen.set_panel_title(
                _("Printing") if self._printer.extrudercount > 0 else _("Working")
            )
        elif state == "complete":
            self.update_progress(1)
            self._screen.set_panel_title(_("Complete"))
            # Auto home Z axis and reset Z-offset to 0 after print completion
            logging.info("Auto-homing Z axis and resetting Z-offset to 0.00 after print completion")
            # First: Home Z axis (physical movement to home position)
            self._screen._send_action(None, "printer.gcode.script", {"script": "G28 Z"})
            # Second: Reset Z-offset to 0 (same as Fine Tuning reset button)
            if self.zoffset != 0:
                self._screen._send_action(None, "printer.gcode.script", {"script": "SET_GCODE_OFFSET Z=0 MOVE=1"})
                self.zoffset = 0.0
            # Don't save print history here anymore - it will be saved when quality is selected
            self._add_timeout(self._config.get_main_config().getint("job_complete_timeout", 0))
        elif state == "error":
            self._screen.set_panel_title(_("Error"))
            self._screen.show_popup_message(msg)
            self._add_timeout(self._config.get_main_config().getint("job_error_timeout", 0))
        elif state == "cancelling":
            self._screen.set_panel_title(_("Cancelling"))
        elif state == "cancelled" or (state == "standby" and self.state == "cancelled"):
            self._screen.set_panel_title(_("Cancelled"))
            self._add_timeout(self._config.get_main_config().getint("job_cancelled_timeout", 0))
        elif state == "paused":
            self._screen.set_panel_title(_("Paused"))
        elif state == "standby":
            self._screen.set_panel_title(_("Standby"))
        if self.state != state:
            logging.debug(f"Changing job_status state from '{self.state}' to '{state}'")
            self.state = state
            if self.thumb_dialog:
                self.close_dialog(self.thumb_dialog)
        self.show_buttons_for_state()

    def _add_timeout(self, timeout):
        self._screen.screensaver.close()
        if timeout != 0:
            GLib.timeout_add_seconds(timeout, self.close_panel)

    def show_buttons_for_state(self):
        # Clear all children from button grid to ensure clean state
        for child in self.buttons['button_grid'].get_children():
            self.buttons['button_grid'].remove(child)

        # Show/hide extrusion controls depending on state
        if self.state == "complete":
            self.extruder_box.set_visible(False)
            self.save_rates_button.set_visible(False)
            # Show quality selection screen (1-8 buttons for good prints)
            self.show_quality_selection()
            self.can_close = False
        else:
            self.extruder_box.set_visible(True)
            self.save_rates_button.set_visible(True)
            if self.state == "printing":
                self.buttons['button_grid'].attach(self.buttons['pause'], 0, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['cancel'], 1, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['fine_tune'], 2, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['control'], 3, 0, 1, 1)
                self.enable_button("pause", "cancel")
                self.can_close = False
            elif self.state == "paused":
                self.buttons['button_grid'].attach(self.buttons['resume'], 0, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['cancel'], 1, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['fine_tune'], 2, 0, 1, 1)
                self.buttons['button_grid'].attach(self.buttons['control'], 3, 0, 1, 1)
                self.enable_button("resume", "cancel")
                self.can_close = False
            else:
                offset = self._printer.get_stat("gcode_move", "homing_origin")
                self.zoffset = float(offset[2]) if offset else 0
                if self.zoffset != 0:
                    if "Z_OFFSET_APPLY_ENDSTOP" in self._printer.available_commands:
                        self.buttons['button_grid'].attach(self.buttons["save_offset_endstop"], 0, 0, 1, 1)
                    else:
                        self.buttons['button_grid'].attach(Gtk.Label(), 0, 0, 1, 1)
                    if "Z_OFFSET_APPLY_PROBE" in self._printer.available_commands:
                        self.buttons['button_grid'].attach(self.buttons["save_offset_probe"], 1, 0, 1, 1)
                    else:
                        self.buttons['button_grid'].attach(Gtk.Label(), 1, 0, 1, 1)
                else:
                    self.buttons['button_grid'].attach(Gtk.Label(), 0, 0, 1, 1)
                    self.buttons['button_grid'].attach(Gtk.Label(), 1, 0, 1, 1)

                if self.filename:
                    self.buttons['button_grid'].attach(self.buttons['restart'], 2, 0, 1, 1)
                    self.enable_button("restart")
                else:
                    self.disable_button("restart")
                if self.state != "cancelling":
                    self.buttons['button_grid'].attach(self.buttons['menu'], 3, 0, 1, 1)
                    self.can_close = True
        self.content.show_all()
        if self.state == "complete":
            self.extruder_box.set_visible(False)

    def show_quality_selection(self):
        """Show the quality selection screen with 0-8 buttons (3x3 grid) et la case 'last print'"""
        # Add title label
        title_label = Gtk.Label(label=_("How many good prints?"))
        title_label.get_style_context().add_class("printing-status")
        title_label.set_halign(Gtk.Align.CENTER)
        self.buttons['button_grid'].attach(title_label, 0, 0, 3, 1)

        # Add quality buttons 0-8 in a 3x3 grid

        for i in range(0, 9):
            row = (i // 3) + 1
            col = i % 3
            self.buttons['button_grid'].attach(self.quality_buttons[f'quality_{i}'], col, row, 1, 1)

        self.buttons['button_grid'].attach(self.last_print_checkbox, 0, 4, 3, 1)
        self.buttons['button_grid'].attach(self.buttons['menu'], 0, 5, 3, 1)

        # Always hide extruder_box after building quality selection UI
        self.extruder_box.set_visible(False)

    def update_filename(self, filename):
        if not filename or filename == self.filename:
            return

        self.filename = filename
        logging.debug(f"Updating filename to {filename}")

        # Load product-specific rates from JSON based on new filename
        product_key = self._get_product_key(filename)
        data = self._read_rates_file()

        # Check for temporary session rates first
        if product_key in Panel._temp_rates:
            rates = Panel._temp_rates[product_key]
            orange_rate = rates.get('orange', None)
            white_rate = rates.get('white', None)
        else:
            orange_rate = None
            white_rate = None

        # If no temp rates, load from JSON
        if orange_rate is None:
            if product_key in data and 'orange' in data[product_key]:
                orange_rate = data[product_key]['orange']
            else:
                orange_rate = data['orange']

        if white_rate is None:
            if product_key in data and 'white' in data[product_key]:
                white_rate = data[product_key]['white']
            else:
                white_rate = data['white']

        # Apply the rates to the inputs
        self.orange_input.set_value(orange_rate)
        self.white_input.set_value(white_rate)

        logging.info(f"FILENAME UPDATED: {filename} → Product: {product_key} → Orange: {orange_rate}%, White: {white_rate}%")
        self.labels["file"].set_label(os.path.splitext(self.filename)[0])

        # Update the file icon based on filename
        icon_name = self.get_file_icon(self.filename)
        self.labels['file_icon'].set_from_pixbuf(self._gtk.PixbufFromIcon(icon_name, self._gtk.font_size * 12))  # Updated to match creation size

        self.filename_label = {
            "complete": self.labels['file'].get_label(),
            "current": self.labels['file'].get_label(),
        }

        self.get_file_metadata()

    def _get_product_key(self, filename=None):
        # Helper to get the product key from filename
        fname = filename or self.filename or ""
        fname = fname.lower()
        if "salmon" in fname:
            return "Salmon"
        elif "blanco" in fname:
            return "EL BLANCO"
        elif "veganvita" in fname:
            return "VEGANVITA"
        elif "prime" in fname or "cut" in fname:
            return "PRIME CUT"
        else:
            return "UNKNOWN"

    def animate_label(self):
        if ellipsized := self.labels['file'].get_layout().is_ellipsized():
            self.filename_label['current'] = self.filename_label['current'][1:]
            self.labels['file'].set_label(self.filename_label['current'] + " " * 6)
        else:
            self.filename_label['current'] = self.filename_label['complete']
            self.labels['file'].set_label(self.filename_label['complete'])
        return True

    def get_file_icon(self, filename):
        """Determine the appropriate icon based on filename keywords"""
        if not filename:
            return "file"
        filename_lower = filename.lower()
        if "salmon" in filename_lower:
            return "salmon"
        elif "blanco" in filename_lower:
            return "elblanco"
        elif "prime" in filename_lower or "cut" in filename_lower:
            return "primecut"
        else:
            return "file"

    def get_file_metadata(self, response=False):
        if self._files.file_metadata_exists(self.filename):
            self._update_file_metadata()
        elif not response:
            logging.debug("Cannot find file metadata. Listening for updated metadata")
            self._files.request_metadata(self.filename)
        else:
            logging.debug("Cannot load file metadata")

    def _update_file_metadata(self):
        self.file_metadata = self._files.get_file_info(self.filename)
        logging.info(f"Update Metadata. File: {self.filename} Size: {self.file_metadata['size']}")
        if "estimated_time" in self.file_metadata:
            if self.timeleft_type == "slicer":
                self.labels["est_time"].set_label(self.format_time(self.file_metadata['estimated_time']))
            self.labels["slicer_time"].set_label(self.format_time(self.file_metadata['estimated_time']))
        if "object_height" in self.file_metadata:
            self.oheight = float(self.file_metadata['object_height'])
            self.labels['height'].set_label(f"{self.oheight:.2f} {self.mm}")
        if "filament_total" in self.file_metadata:
            self.labels['filament_total'].set_label(f"{float(self.file_metadata['filament_total']) / 1000:.1f} m")
        if "job_id" in self.file_metadata and self.file_metadata['job_id']:
            history = self._screen.apiclient.send_request(f"server/history/job?uid={self.file_metadata['job_id']}")
            if history and history['job']['status'] == "completed" and history['job']['print_duration']:
                self.file_metadata["last_time"] = history['job']['print_duration']
