# -*- coding: utf-8 -*-
import logging
import os
import re
import threading
from typing import Dict, Any, List
import requests

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, GLib
from ks_includes.screen_panel import ScreenPanel

class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or _("Printer Configuration")
        super().__init__(screen, title)
        self.config_data = {}
        self.config_widgets = {}
        self.original_config_content = ""
        self.menu = ['config_menu']
        
        # Configuration sections to display with their parameters
        self.config_sections = {
            'printer': {
                'name': _('Printer Settings'),
                'params': {
                    'kinematics': {'type': 'text', 'name': _('Kinematics')},
                    'max_velocity': {'type': 'number', 'name': _('Max Velocity'), 'min': 10, 'max': 1000, 'step': 10},
                    'max_accel': {'type': 'number', 'name': _('Max Acceleration'), 'min': 10, 'max': 5000, 'step': 10},
                    'max_z_velocity': {'type': 'number', 'name': _('Max Z Velocity'), 'min': 1, 'max': 100, 'step': 1},
                    'max_z_accel': {'type': 'number', 'name': _('Max Z Acceleration'), 'min': 10, 'max': 500, 'step': 10}
                }
            },
            'stepper_x': {
                'name': _('X Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 200, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_endstop': {'type': 'number', 'name': _('Position Endstop'), 'min': -100, 'max': 500, 'step': 1},
                    'position_max': {'type': 'number', 'name': _('Position Max'), 'min': 1, 'max': 1000, 'step': 10},
                    'position_min': {'type': 'number', 'name': _('Position Min'), 'min': -100, 'max': 100, 'step': 1},
                    'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 200, 'step': 5},
                    'homing_retract_dist': {'type': 'number', 'name': _('Homing Retract Dist'), 'min': 1, 'max': 50, 'step': 1}
                }
            },
            'stepper_y': {
                'name': _('Y Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 300, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_endstop': {'type': 'number', 'name': _('Position Endstop'), 'min': -200, 'max': 500, 'step': 1},
                    'position_max': {'type': 'number', 'name': _('Position Max'), 'min': 1, 'max': 200000, 'step': 1000},
                    'position_min': {'type': 'number', 'name': _('Position Min'), 'min': -200000, 'max': 1000, 'step': 1000},
                    'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 300, 'step': 5},
                    'homing_retract_dist': {'type': 'number', 'name': _('Homing Retract Dist'), 'min': 1, 'max': 50, 'step': 1},
                    'homing_positive_dir': {'type': 'boolean', 'name': _('Homing Positive Dir')}
                }
            },
            'stepper_z': {
                'name': _('Z Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 50, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_endstop': {'type': 'decimal', 'name': _('Position Endstop'), 'min': 1, 'max': 300, 'step': 0.1},
                    'position_max': {'type': 'decimal', 'name': _('Position Max'), 'min': 1, 'max': 300, 'step': 0.1},
                    'position_min': {'type': 'number', 'name': _('Position Min'), 'min': 0, 'max': 50, 'step': 1},
                    'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 100, 'step': 1},
                    'homing_retract_dist': {'type': 'number', 'name': _('Homing Retract Dist'), 'min': 1, 'max': 20, 'step': 1}
                }
            },
            'extruder': {
                'name': _('Extruder Orange'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'number', 'name': _('Rotation Distance'), 'min': 1, 'max': 100, 'step': 1},
                    'nozzle_diameter': {'type': 'decimal', 'name': _('Nozzle Diameter'), 'min': 0.1, 'max': 2.0, 'step': 0.1},
                    'filament_diameter': {'type': 'decimal', 'name': _('Filament Diameter'), 'min': 1.0, 'max': 5.0, 'step': 0.25},
                    'heater_pin': {'type': 'text', 'name': _('Heater Pin')},
                    'control': {'type': 'text', 'name': _('Control')},
                    'min_extrude_temp': {'type': 'number', 'name': _('Min Extrude Temp'), 'min': -300, 'max': 100, 'step': 1},
                    'min_temp': {'type': 'number', 'name': _('Min Temperature'), 'min': -300, 'max': 100, 'step': 1},
                    'max_temp': {'type': 'number', 'name': _('Max Temperature'), 'min': 50, 'max': 500, 'step': 10},
                    'max_extrude_only_distance': {'type': 'number', 'name': _('Max Extrude Distance'), 'min': 50, 'max': 5000000, 'step': 100000},
                    'max_extrude_cross_section': {'type': 'number', 'name': _('Max Cross Section'), 'min': 50, 'max': 5000000, 'step': 100000},
                    'sensor_type': {'type': 'text', 'name': _('Sensor Type')},
                    'sensor_pin': {'type': 'text', 'name': _('Sensor Pin')}
                }
            },
            'extruder1': {
                'name': _('Extruder White'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'number', 'name': _('Rotation Distance'), 'min': 1, 'max': 100, 'step': 1},
                    'nozzle_diameter': {'type': 'decimal', 'name': _('Nozzle Diameter'), 'min': 0.1, 'max': 2.0, 'step': 0.1},
                    'filament_diameter': {'type': 'decimal', 'name': _('Filament Diameter'), 'min': 1.0, 'max': 5.0, 'step': 0.25},
                    'heater_pin': {'type': 'text', 'name': _('Heater Pin')},
                    'control': {'type': 'text', 'name': _('Control')},
                    'pid_Kp': {'type': 'decimal', 'name': _('PID Kp'), 'min': 0.1, 'max': 100.0, 'step': 0.1},
                    'pid_Ki': {'type': 'decimal', 'name': _('PID Ki'), 'min': 0.01, 'max': 10.0, 'step': 0.01},
                    'pid_Kd': {'type': 'number', 'name': _('PID Kd'), 'min': 1, 'max': 1000, 'step': 1},
                    'min_extrude_temp': {'type': 'number', 'name': _('Min Extrude Temp'), 'min': -300, 'max': 100, 'step': 1},
                    'min_temp': {'type': 'number', 'name': _('Min Temperature'), 'min': -300, 'max': 100, 'step': 1},
                    'max_temp': {'type': 'number', 'name': _('Max Temperature'), 'min': 50, 'max': 50000, 'step': 100},
                    'max_extrude_only_distance': {'type': 'number', 'name': _('Max Extrude Distance'), 'min': 50, 'max': 5000000, 'step': 100000},
                    'max_extrude_cross_section': {'type': 'number', 'name': _('Max Cross Section'), 'min': 50, 'max': 5000000, 'step': 100000},
                    'sensor_type': {'type': 'text', 'name': _('Sensor Type')},
                    'sensor_pin': {'type': 'text', 'name': _('Sensor Pin')}
                }
            },
            'gcode_macro T0': {
                'name': _('T0 Macro (Orange)'),
                'params': {
                    'SET_GCODE_OFFSET_X': {'type': 'number', 'name': _('X Offset'), 'min': -10, 'max': 10, 'step': 0.1},
                    'SET_GCODE_OFFSET_Z_ADJUST': {'type': 'decimal', 'name': _('Z Adjust'), 'min': -5.0, 'max': 5.0, 'step': 0.1},
                    'M220_S': {'type': 'number', 'name': _('Speed Factor %'), 'min': 50, 'max': 500, 'step': 10},
                    'M221_S': {'type': 'number', 'name': _('Extrude Factor %'), 'min': 50, 'max': 500, 'step': 10}
                }
            },
            'gcode_macro T1': {
                'name': _('T1 Macro (White)'),
                'params': {
                    'SET_GCODE_OFFSET_X': {'type': 'number', 'name': _('X Offset'), 'min': -10, 'max': 10, 'step': 0.1},
                    'SET_GCODE_OFFSET_Y': {'type': 'number', 'name': _('Y Offset'), 'min': -10, 'max': 10, 'step': 0.1},
                    'SET_GCODE_OFFSET_Z_ADJUST': {'type': 'decimal', 'name': _('Z Adjust'), 'min': -5.0, 'max': 5.0, 'step': 0.1},
                    'M220_S': {'type': 'number', 'name': _('Speed Factor %'), 'min': 50, 'max': 500, 'step': 10},
                    'M221_S': {'type': 'number', 'name': _('Extrude Factor %'), 'min': 50, 'max': 500, 'step': 10}
                }
            }
        }
        
        self.create_main_menu()
        self.load_config_data()

    def create_main_menu(self):
        """Create the main configuration menu with section buttons"""
        self.labels['config_menu'] = self._gtk.ScrolledWindow()
        self.labels['config'] = Gtk.Grid()
        self.labels['config_menu'].add(self.labels['config'])
        
        # Add save and reload buttons FIRST (at the top)
        self.add_action_buttons()
        
        # Add sections as menu items AFTER (below the action buttons)
        for section_key, section_data in self.config_sections.items():
            self.add_section_option(section_key, section_data)
        
        self.content.add(self.labels['config_menu'])

    def add_section_option(self, section_key: str, section_data: Dict[str, Any]):
        """Add a section option to the main menu"""
        name = Gtk.Label(
            hexpand=True, vexpand=True, halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
        name.set_markup(f"<big><b>{section_data['name']}</b></big>")

        row_box = Gtk.Box(spacing=5, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        row_box.get_style_context().add_class("frame-item")
        row_box.add(name)

        open_section = self._gtk.Button("settings", style="main_menu_control")
        open_section.connect("clicked", self.load_section_menu, section_key, section_data['name'])
        open_section.set_hexpand(False)
        open_section.set_halign(Gtk.Align.END)
        row_box.add(open_section)

        # Get current number of rows to position correctly
        current_rows = len([child for child in self.labels['config'].get_children()])
        self.labels['config'].insert_row(current_rows)
        self.labels['config'].attach(row_box, 0, current_rows, 1, 1)
        
    def add_action_buttons(self):
        """Add save and reload action buttons"""
        # Save button
        save_name = Gtk.Label(
            hexpand=True, vexpand=True, halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
        save_name.set_markup(f"<big><b>{_('Save Configuration')}</b></big>")

        save_row = Gtk.Box(spacing=5, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        save_row.get_style_context().add_class("frame-item")
        save_row.add(save_name)

        save_button = self._gtk.Button("sd", style="main_menu_production")
        save_button.connect("clicked", self.save_config)
        save_button.set_hexpand(False)
        save_button.set_halign(Gtk.Align.END)
        save_row.add(save_button)

        # Reload button
        reload_name = Gtk.Label(
            hexpand=True, vexpand=True, halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
        reload_name.set_markup(f"<big><b>{_('Reload Configuration')}</b></big>")

        reload_row = Gtk.Box(spacing=5, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        reload_row.get_style_context().add_class("frame-item")
        reload_row.add(reload_name)

        reload_button = self._gtk.Button("refresh", style="industrial_primary")
        reload_button.connect("clicked", self.reload_config)
        reload_button.set_hexpand(False)
        reload_button.set_halign(Gtk.Align.END)
        reload_row.add(reload_button)

        # Get current number of rows to position correctly (now will be 0 and 1 since we add these first)
        current_rows = len([child for child in self.labels['config'].get_children()])
        
        # Add save button
        self.labels['config'].insert_row(current_rows)
        self.labels['config'].attach(save_row, 0, current_rows, 1, 1)
        
        # Add reload button
        self.labels['config'].insert_row(current_rows + 1)
        self.labels['config'].attach(reload_row, 0, current_rows + 1, 1, 1)

    def load_section_menu(self, widget, section_key: str, section_name: str):
        """Load a specific configuration section menu"""
        logging.info(f"Loading section menu: {section_key}")
        
        menu_key = f"{section_key}_menu"
        if menu_key not in self.labels:
            self.create_section_menu(section_key, section_name)
        
        self.load_menu(widget, section_key, section_name)

    def create_section_menu(self, section_key: str, section_name: str):
        """Create the menu for a specific configuration section"""
        menu_key = f"{section_key}_menu"
        self.labels[menu_key] = self._gtk.ScrolledWindow()
        self.labels[section_key] = Gtk.Grid()
        self.labels[menu_key].add(self.labels[section_key])
        
        if section_key not in self.config_widgets:
            self.config_widgets[section_key] = {}
        
        section_config = self.config_sections[section_key]
        section_data = self.config_data.get(section_key, {})
        
        pos = 0
        for param_key, param_config in section_config['params'].items():
            current_value = section_data.get(param_key, '')
            widget = self.create_parameter_widget(section_key, param_key, param_config, current_value)
            
            if widget:
                self.labels[section_key].insert_row(pos)
                self.labels[section_key].attach(widget, 0, pos, 1, 1)
                pos += 1

    def create_parameter_widget(self, section_key: str, param_key: str, param_config: Dict[str, Any], current_value: str):
        """Create a widget for a configuration parameter"""
        name = Gtk.Label(
            hexpand=True, vexpand=False, halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
        name.set_markup(f"<b>{param_config['name']}</b>")
        name.set_size_request(200, -1)

        row_box = Gtk.Box(spacing=10, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        row_box.get_style_context().add_class("frame-item")
        row_box.set_margin_top(5)
        row_box.set_margin_bottom(5)
        row_box.add(name)

        param_type = param_config['type']
        
        # Get the current value from loaded data
        actual_value = ""
        if section_key in self.config_data and param_key in self.config_data[section_key]:
            actual_value = self.config_data[section_key][param_key]
        
        if param_type == 'text':
            # Create text entry with auto keyboard support
            entry_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            entry_box.set_halign(Gtk.Align.END)
            entry_box.set_hexpand(False)
            
            entry = Gtk.Entry()
            entry.set_text(str(actual_value) if actual_value else "")
            entry.set_size_request(200, -1)
            entry.connect("changed", self.on_text_changed, section_key, param_key)
            # Auto-show keyboard on focus
            entry.connect("focus-in-event", self.on_entry_focus_in)
            entry.connect("focus-out-event", self.on_entry_focus_out)
            
            entry_box.add(entry)
            row_box.add(entry_box)
            self.config_widgets[section_key][param_key] = entry
            
        elif param_type in ['number', 'decimal']:
            # Create -/entry/+ layout for number input
            value_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            value_box.set_halign(Gtk.Align.END)
            value_box.set_hexpand(False)
            
            # Decrease button
            decrease_btn = self._gtk.Button("minus", style="background_color")
            decrease_btn.set_size_request(50, 50)
            decrease_btn.connect("clicked", self.on_number_changed, section_key, param_key, -param_config.get('step', 1))
            
            # Text entry for direct input
            entry = Gtk.Entry()
            display_value = str(actual_value) if actual_value else "0"
            entry.set_text(display_value)
            entry.set_size_request(120, -1)
            entry.set_halign(Gtk.Align.CENTER)
            entry.set_valign(Gtk.Align.CENTER)
            entry.get_style_context().add_class("temperature_entry")
            entry.connect("changed", self.on_number_entry_changed, section_key, param_key, param_config)
            # Auto-show keyboard on focus for numbers too
            entry.connect("focus-in-event", self.on_entry_focus_in)
            entry.connect("focus-out-event", self.on_entry_focus_out)
            
            # Increase button
            increase_btn = self._gtk.Button("plus", style="background_color")
            increase_btn.set_size_request(50, 50)
            increase_btn.connect("clicked", self.on_number_changed, section_key, param_key, param_config.get('step', 1))
            
            value_box.add(decrease_btn)
            value_box.add(entry)
            value_box.add(increase_btn)
            row_box.add(value_box)
            
            self.config_widgets[section_key][param_key] = {
                'entry': entry,
                'min': param_config.get('min', 0),
                'max': param_config.get('max', 1000),
                'step': param_config.get('step', 1),
                'is_decimal': param_type == 'decimal'
            }
            
        elif param_type == 'boolean':
            # Create True/False buttons
            value_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            value_box.set_halign(Gtk.Align.END)
            value_box.set_hexpand(False)
            
            # False button
            false_btn = Gtk.Button("False")
            false_btn.set_size_request(80, 50)
            false_btn.connect("clicked", self.on_boolean_changed, section_key, param_key, "false")
            
            # True button
            true_btn = Gtk.Button("True")
            true_btn.set_size_request(80, 50)
            true_btn.connect("clicked", self.on_boolean_changed, section_key, param_key, "true")
            
            value_box.add(false_btn)
            value_box.add(true_btn)
            row_box.add(value_box)
            
            # Store both buttons for color management
            self.config_widgets[section_key][param_key] = {
                'true_btn': true_btn,
                'false_btn': false_btn,
                'current_value': str(actual_value).lower() if actual_value else "false"
            }
            
            # Set initial button colors
            bool_value = str(actual_value).lower() if actual_value else "false"
            self.update_boolean_buttons(section_key, param_key, bool_value)

        return row_box

    def on_text_changed(self, entry, section_key: str, param_key: str):
        """Handle text entry changes"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
        self.config_data[section_key][param_key] = entry.get_text()

    def on_number_entry_changed(self, entry, section_key: str, param_key: str, param_config: Dict[str, Any]):
        """Handle direct numeric entry changes"""
        try:
            text_value = entry.get_text()
            
            # Allow empty for intermediate states
            if not text_value:
                if section_key not in self.config_data:
                    self.config_data[section_key] = {}
                self.config_data[section_key][param_key] = ""
                return
            
            # Validate the entered value
            if param_config.get('type') == 'decimal':
                value = float(text_value)
            else:
                value = int(float(text_value))
            
            # Apply min/max constraints
            min_val = param_config.get('min', 0)
            max_val = param_config.get('max', 1000)
            
            if value < min_val:
                value = min_val
                entry.set_text(str(value))
            elif value > max_val:
                value = max_val
                entry.set_text(str(value))
            
            # Store the valid value
            if section_key not in self.config_data:
                self.config_data[section_key] = {}
            self.config_data[section_key][param_key] = str(value)
            
        except ValueError:
            # Invalid input - revert to last valid value or default
            if (section_key in self.config_data and 
                param_key in self.config_data[section_key] and
                self.config_data[section_key][param_key]):
                entry.set_text(str(self.config_data[section_key][param_key]))
            else:
                entry.set_text("0")

    def on_entry_focus_in(self, entry, event):
        """Handle entry focus in - show virtual keyboard"""
        try:
            logging.info("Entry focused - attempting to show keyboard")
            # Show virtual keyboard for text input using KlipperScreen's method
            if hasattr(self._screen, '_show_keyboard'):
                self._screen._show_keyboard(entry)
                logging.info("Keyboard shown via _screen._show_keyboard")
            elif hasattr(self._screen, 'show_keyboard'):
                self._screen.show_keyboard(entry)
                logging.info("Keyboard shown via _screen.show_keyboard")
            elif hasattr(self._screen, 'base_panel') and hasattr(self._screen.base_panel, 'show_keyboard'):
                self._screen.base_panel.show_keyboard(entry)
                logging.info("Keyboard shown via base_panel.show_keyboard")
            else:
                logging.warning("No keyboard method found")
        except Exception as e:
            logging.debug(f"Could not show virtual keyboard: {e}")
        return False

    def on_entry_focus_out(self, entry, event):
        """Handle entry focus out - hide virtual keyboard"""
        try:
            logging.info("Entry focus lost - attempting to hide keyboard")
            # Hide virtual keyboard using KlipperScreen's method
            if hasattr(self._screen, '_hide_keyboard'):
                self._screen._hide_keyboard()
                logging.info("Keyboard hidden via _screen._hide_keyboard")
            elif hasattr(self._screen, 'hide_keyboard'):
                self._screen.hide_keyboard()
                logging.info("Keyboard hidden via _screen.hide_keyboard")
            elif hasattr(self._screen, 'base_panel') and hasattr(self._screen.base_panel, 'hide_keyboard'):
                self._screen.base_panel.hide_keyboard()
                logging.info("Keyboard hidden via base_panel.hide_keyboard")
        except Exception as e:
            logging.debug(f"Could not hide virtual keyboard: {e}")
        return False

    def on_number_changed(self, widget, section_key: str, param_key: str, delta):
        """Handle number increment/decrement using +/- buttons"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
            
        widget_data = self.config_widgets[section_key][param_key]
        entry = widget_data['entry']
        current_text = entry.get_text()
        
        try:
            if widget_data['is_decimal']:
                current_value = float(current_text) if current_text else 0.0
                new_value = max(widget_data['min'], min(widget_data['max'], current_value + delta))
                formatted_value = f"{new_value:.1f}"
            else:
                current_value = int(float(current_text)) if current_text else 0
                new_value = max(widget_data['min'], min(widget_data['max'], current_value + int(delta)))
                formatted_value = str(new_value)
                
            entry.set_text(formatted_value)
            self.config_data[section_key][param_key] = formatted_value
            
        except ValueError:
            logging.error(f"Invalid number format: {current_text}")

    def on_boolean_changed(self, widget, section_key: str, param_key: str, value: str):
        """Handle boolean button changes"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
        
        self.config_data[section_key][param_key] = value
        
        # Update button colors
        self.update_boolean_buttons(section_key, param_key, value.lower())

    def update_boolean_buttons(self, section_key: str, param_key: str, value: str):
        """Update the colors of boolean buttons based on selection"""
        if (section_key in self.config_widgets and 
            param_key in self.config_widgets[section_key] and
            isinstance(self.config_widgets[section_key][param_key], dict)):
            
            widget_data = self.config_widgets[section_key][param_key]
            true_btn = widget_data['true_btn']
            false_btn = widget_data['false_btn']
            
            # Remove all color classes first
            for btn in [true_btn, false_btn]:
                context = btn.get_style_context()
                context.remove_class("color1")
                context.remove_class("color2")
                context.remove_class("color3")
                context.remove_class("color4")
                context.remove_class("main_menu_production")
                context.remove_class("background_color")
            
            # Set colors based on selection
            if value.lower() in ['true', '1', 'yes']:
                true_btn.get_style_context().add_class("main_menu_production")  # Selected (orange)
                false_btn.get_style_context().add_class("background_color")  # Unselected (background)
                widget_data['current_value'] = 'true'
            else:
                true_btn.get_style_context().add_class("background_color")  # Unselected (background)
                false_btn.get_style_context().add_class("main_menu_production")  # Selected (orange)
                widget_data['current_value'] = 'false'


    def on_dropdown_changed(self, combo, section_key: str, param_key: str):
        """Handle dropdown changes"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
        self.config_data[section_key][param_key] = combo.get_active_text()

    def load_config_data(self):
        """Load current printer configuration from file"""
        def load_async():
            try:
                config_path = "/home/pi/printer_data/config/printer.cfg"
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        self.original_config_content = f.read()
                    self._parse_config_file(self.original_config_content)
                else:
                    logging.error(f"Config file not found: {config_path}")
                    GLib.idle_add(self._screen.show_popup_message, _("Configuration file not found"))
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                GLib.idle_add(self._screen.show_popup_message, f"Error loading config: {e}")
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=load_async)
        thread.daemon = True
        thread.start()

    def _parse_config_file(self, config_text: str):
        """Parse the printer.cfg file to extract current values"""
        self.config_data = {}
        lines = config_text.split('\n')
        current_section = None
        current_gcode = []
        in_gcode_section = False
        
        logging.info("Parsing printer.cfg file...")
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Check for section headers
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1].strip()
                in_gcode_section = current_section.startswith('gcode_macro')
                current_gcode = []
                
                # Only process sections we care about
                if current_section in self.config_sections:
                    if current_section not in self.config_data:
                        self.config_data[current_section] = {}
                continue
            
            # Process parameters in supported sections
            if current_section and current_section in self.config_sections:
                if in_gcode_section:
                    # Handle gcode_macro sections differently
                    if line.startswith('gcode:'):
                        continue
                    elif line.strip() and not line.startswith('variable_'):
                        current_gcode.append(line.strip())
                        # Parse gcode commands for macro parameters
                        self._parse_gcode_line(current_section, line.strip())
                else:
                    # Regular config sections
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove comments from value
                        if '#' in value:
                            value = value.split('#')[0].strip()
                        
                        # Only store if it's a parameter we care about
                        if key in self.config_sections[current_section]['params']:
                            self.config_data[current_section][key] = value
        
        # Initialize empty sections for missing ones
        for section_name in self.config_sections.keys():
            if section_name not in self.config_data:
                self.config_data[section_name] = {}
                
        logging.info(f"Configuration parsing completed. Found sections: {list(self.config_data.keys())}")
        
        # Update the widgets on the main thread
        GLib.idle_add(self.update_widgets)

    def _parse_gcode_line(self, section_key: str, line: str):
        """Parse gcode commands to extract parameter values"""
        line = line.strip()
        
        # Parse SET_GCODE_OFFSET commands
        if 'SET_GCODE_OFFSET' in line:
            if 'X=' in line:
                match = re.search(r'X=([+-]?\d*\.?\d+)', line)
                if match:
                    self.config_data[section_key]['SET_GCODE_OFFSET_X'] = match.group(1)
            
            if 'Y=' in line:
                match = re.search(r'Y=([+-]?\d*\.?\d+)', line)
                if match:
                    self.config_data[section_key]['SET_GCODE_OFFSET_Y'] = match.group(1)
            
            if 'Z_ADJUST=' in line:
                match = re.search(r'Z_ADJUST=([+-]?\d*\.?\d+)', line)
                if match:
                    self.config_data[section_key]['SET_GCODE_OFFSET_Z_ADJUST'] = match.group(1)
        
        # Parse M220 speed factor
        if line.startswith('M220'):
            match = re.search(r'[sS](\d+)', line)
            if match:
                self.config_data[section_key]['M220_S'] = match.group(1)
        
        # Parse M221 extrude factor
        if line.startswith('M221'):
            match = re.search(r'[sS](\d+)', line)
            if match:
                self.config_data[section_key]['M221_S'] = match.group(1)

    def update_widgets(self):
        """Update widgets with loaded configuration data"""
        logging.info("=== UPDATING WIDGETS ===")
        logging.info(f"Available config sections: {list(self.config_data.keys())}")
        
        for section_key, section_data in self.config_data.items():
            if section_key in self.config_widgets:
                for param_key, param_value in section_data.items():
                    if param_key in self.config_widgets[section_key]:
                        widget = self.config_widgets[section_key][param_key]
                        
                        if isinstance(widget, Gtk.Entry):
                            widget.set_text(str(param_value))
                        elif isinstance(widget, dict):
                            if 'entry' in widget:  # Number widget
                                widget['entry'].set_text(str(param_value))
                            elif 'true_btn' in widget:  # Boolean widget
                                self.update_boolean_buttons(section_key, param_key, str(param_value).lower())
                                
        logging.info("=== WIDGET UPDATE COMPLETED ===")
        
        # Show a confirmation message
        GLib.idle_add(self._screen.show_popup_message, _("Configuration loaded successfully"))

    def save_config(self, widget):
        """Save configuration changes to printer.cfg"""
        def save_async():
            try:
                # Modify the original config content with new values
                modified_config = self.modify_existing_config(self.original_config_content)
                
                # Write back to file
                config_path = "/home/pi/printer_data/config/printer.cfg"
                with open(config_path, 'w') as f:
                    f.write(modified_config)
                
                GLib.idle_add(self._on_config_saved_success)
                
            except Exception as e:
                logging.error(f"Error saving config: {e}")
                GLib.idle_add(self._on_config_saved_error, str(e))
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=save_async)
        thread.daemon = True
        thread.start()

    def modify_existing_config(self, config_text: str) -> str:
        """Modify the existing configuration with new values while preserving structure"""
        lines = config_text.split('\n')
        modified_lines = []
        current_section = None
        in_gcode_section = False
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # Check for section headers
            if line_stripped.startswith('[') and line_stripped.endswith(']'):
                current_section = line_stripped[1:-1].strip()
                in_gcode_section = current_section.startswith('gcode_macro')
                modified_lines.append(original_line)
                continue
            
            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith('#'):
                modified_lines.append(original_line)
                continue
            
            # Process parameters in supported sections
            if current_section and current_section in self.config_sections:
                if in_gcode_section:
                    # Handle gcode_macro sections
                    if line_stripped.startswith('gcode:'):
                        modified_lines.append(original_line)
                        continue
                    
                    # Modify gcode commands
                    modified_line = self._modify_gcode_line(current_section, original_line)
                    modified_lines.append(modified_line)
                else:
                    # Regular config sections
                    if ':' in line_stripped:
                        key = line_stripped.split(':', 1)[0].strip()
                        
                        # Check if we have a new value for this key
                        if (current_section in self.config_data and 
                            key in self.config_data[current_section] and
                            key in self.config_sections[current_section]['params']):
                            
                            new_value = self.config_data[current_section][key]
                            
                            # Preserve indentation and comments
                            indent = len(original_line) - len(original_line.lstrip())
                            comment = ""
                            if '#' in original_line:
                                comment = " " + original_line.split('#', 1)[1]
                            
                            modified_line = " " * indent + f"{key}: {new_value}" + comment
                            modified_lines.append(modified_line)
                        else:
                            modified_lines.append(original_line)
                    else:
                        modified_lines.append(original_line)
            else:
                modified_lines.append(original_line)
        
        return '\n'.join(modified_lines)

    def _modify_gcode_line(self, section_key: str, line: str) -> str:
        """Modify gcode commands with new parameter values"""
        if section_key not in self.config_data:
            return line
        
        modified_line = line
        section_data = self.config_data[section_key]
        
        # Modify SET_GCODE_OFFSET commands
        if 'SET_GCODE_OFFSET' in line:
            if 'SET_GCODE_OFFSET_X' in section_data:
                modified_line = re.sub(r'X=[+-]?\d*\.?\d+', f"X={section_data['SET_GCODE_OFFSET_X']}", modified_line)
            
            if 'SET_GCODE_OFFSET_Y' in section_data:
                modified_line = re.sub(r'Y=[+-]?\d*\.?\d+', f"Y={section_data['SET_GCODE_OFFSET_Y']}", modified_line)
            
            if 'SET_GCODE_OFFSET_Z_ADJUST' in section_data:
                modified_line = re.sub(r'Z_ADJUST=[+-]?\d*\.?\d+', f"Z_ADJUST={section_data['SET_GCODE_OFFSET_Z_ADJUST']}", modified_line)
        
        # Modify M220 speed factor
        if line.strip().startswith('M220') and 'M220_S' in section_data:
            modified_line = re.sub(r'[sS]\d+', f"S{section_data['M220_S']}", modified_line)
        
        # Modify M221 extrude factor
        if line.strip().startswith('M221') and 'M221_S' in section_data:
            modified_line = re.sub(r'[sS]\d+', f"S{section_data['M221_S']}", modified_line)
        
        return modified_line

    def _on_config_saved_success(self):
        """Handle successful config save"""
        logging.info("Configuration saved successfully")
        self._screen.show_popup_message(_("Configuration saved successfully! Restart Klipper to apply changes."))

    def _on_config_saved_error(self, error_msg):
        """Handle config save error"""
        logging.error(f"Save error: {error_msg}")
        self._screen.show_popup_message(_("Failed to save configuration: ") + str(error_msg))

    def reload_config(self, widget):
        """Reload configuration from the printer"""
        self.load_config_data()

    def activate(self):
        """Called when the panel is activated"""
        self.load_config_data()

    def deactivate(self):
        """Called when the panel is deactivated"""
        pass