import gi
import logging
import re
from typing import Dict, Any, List

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, GLib
from ks_includes.screen_panel import ScreenPanel

class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or _("Printer Configuration")
        super().__init__(screen, title)
        self.config_data = {}
        self.config_widgets = {}
        self.menu = ['config_menu']
        
        # Configuration sections to display with their parameters
        # Based on your actual printer.cfg structure
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
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_endstop': {'type': 'number', 'name': _('Position Endstop'), 'min': -500, 'max': 500, 'step': 1},
                    'position_max': {'type': 'number', 'name': _('Position Max'), 'min': 1, 'max': 1000, 'step': 10},
                    'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 100, 'step': 5}
                }
            },
            'stepper_y': {
                'name': _('Y Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_endstop': {'type': 'number', 'name': _('Position Endstop'), 'min': -500, 'max': 500, 'step': 1},
                    'position_max': {'type': 'number', 'name': _('Position Max'), 'min': 1, 'max': 1000, 'step': 10},
                    'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 100, 'step': 5}
                }
            },
            'stepper_z': {
                'name': _('Z Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
                    'position_max': {'type': 'decimal', 'name': _('Position Max'), 'min': 1, 'max': 1000, 'step': 1}
                }
            },
            'stepper_z1': {
                'name': _('Z1 Stepper'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')}
                }
            },
            'extruder': {
                'name': _('Extruder Orange'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'nozzle_diameter': {'type': 'decimal', 'name': _('Nozzle Diameter'), 'min': 0.1, 'max': 10.0, 'step': 0.1},
                    'filament_diameter': {'type': 'decimal', 'name': _('Filament Diameter'), 'min': 1.0, 'max': 20.0, 'step': 0.1},
                    'heater_pin': {'type': 'text', 'name': _('Heater Pin')},
                    'sensor_type': {'type': 'text', 'name': _('Sensor Type')},
                    'sensor_pin': {'type': 'text', 'name': _('Sensor Pin')},
                    'max_temp': {'type': 'number', 'name': _('Max Temperature'), 'min': 50, 'max': 500, 'step': 5},
                    'min_temp': {'type': 'number', 'name': _('Min Temperature'), 'min': -300, 'max': 100, 'step': 5},
                    'min_extrude_temp': {'type': 'number', 'name': _('Min Extrude Temp'), 'min': -300, 'max': 300, 'step': 5},
                    'max_extrude_only_distance': {'type': 'number', 'name': _('Max Extrude Distance'), 'min': 50, 'max': 50000, 'step': 100},
                    'max_extrude_cross_section': {'type': 'number', 'name': _('Max Cross Section'), 'min': 50, 'max': 50000, 'step': 100}
                }
            },
            'extruder1': {
                'name': _('Extruder White'),
                'params': {
                    'step_pin': {'type': 'text', 'name': _('Step Pin')},
                    'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
                    'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
                    'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
                    'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 100, 'step': 0.1},
                    'nozzle_diameter': {'type': 'decimal', 'name': _('Nozzle Diameter'), 'min': 0.1, 'max': 10.0, 'step': 0.1},
                    'filament_diameter': {'type': 'decimal', 'name': _('Filament Diameter'), 'min': 1.0, 'max': 20.0, 'step': 0.1},
                    'heater_pin': {'type': 'text', 'name': _('Heater Pin')},
                    'sensor_type': {'type': 'text', 'name': _('Sensor Type')},
                    'sensor_pin': {'type': 'text', 'name': _('Sensor Pin')},
                    'max_temp': {'type': 'number', 'name': _('Max Temperature'), 'min': 50, 'max': 500, 'step': 5},
                    'min_temp': {'type': 'number', 'name': _('Min Temperature'), 'min': -300, 'max': 100, 'step': 5},
                    'min_extrude_temp': {'type': 'number', 'name': _('Min Extrude Temp'), 'min': -300, 'max': 300, 'step': 5},
                    'max_extrude_only_distance': {'type': 'number', 'name': _('Max Extrude Distance'), 'min': 50, 'max': 50000, 'step': 100},
                    'max_extrude_cross_section': {'type': 'number', 'name': _('Max Cross Section'), 'min': 50, 'max': 50000, 'step': 100}
                }
            },
            'tmc5160 stepper_x': {
                'name': _('TMC5160 X Driver'),
                'params': {
                    'cs_pin': {'type': 'text', 'name': _('CS Pin')},
                    'spi_bus': {'type': 'text', 'name': _('SPI Bus')},
                    'spi_speed': {'type': 'number', 'name': _('SPI Speed'), 'min': 1000000, 'max': 10000000, 'step': 100000},
                    'run_current': {'type': 'decimal', 'name': _('Run Current'), 'min': 0.1, 'max': 3.0, 'step': 0.1},
                    'interpolate': {'type': 'boolean', 'name': _('Interpolate')}
                }
            },
            'tmc5160 stepper_y': {
                'name': _('TMC5160 Y Driver'),
                'params': {
                    'cs_pin': {'type': 'text', 'name': _('CS Pin')},
                    'spi_bus': {'type': 'text', 'name': _('SPI Bus')},
                    'spi_speed': {'type': 'number', 'name': _('SPI Speed'), 'min': 1000000, 'max': 10000000, 'step': 100000},
                    'run_current': {'type': 'decimal', 'name': _('Run Current'), 'min': 0.1, 'max': 3.0, 'step': 0.1},
                    'interpolate': {'type': 'boolean', 'name': _('Interpolate')}
                }
            },
            'tmc5160 stepper_z': {
                'name': _('TMC5160 Z Driver'),
                'params': {
                    'cs_pin': {'type': 'text', 'name': _('CS Pin')},
                    'spi_bus': {'type': 'text', 'name': _('SPI Bus')},
                    'spi_speed': {'type': 'number', 'name': _('SPI Speed'), 'min': 1000000, 'max': 10000000, 'step': 100000},
                    'run_current': {'type': 'decimal', 'name': _('Run Current'), 'min': 0.1, 'max': 3.0, 'step': 0.1},
                    'interpolate': {'type': 'boolean', 'name': _('Interpolate')}
                }
            },
            'tmc5160 stepper_z1': {
                'name': _('TMC5160 Z1 Driver'),
                'params': {
                    'cs_pin': {'type': 'text', 'name': _('CS Pin')},
                    'spi_bus': {'type': 'text', 'name': _('SPI Bus')},
                    'spi_speed': {'type': 'number', 'name': _('SPI Speed'), 'min': 1000000, 'max': 10000000, 'step': 100000},
                    'run_current': {'type': 'decimal', 'name': _('Run Current'), 'min': 0.1, 'max': 3.0, 'step': 0.1},
                    'interpolate': {'type': 'boolean', 'name': _('Interpolate')}
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
        name.set_size_request(200, -1)  # Fixed width for consistent alignment

        row_box = Gtk.Box(spacing=10, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        row_box.get_style_context().add_class("frame-item")
        row_box.set_margin_top(5)
        row_box.set_margin_bottom(5)
        row_box.add(name)

        param_type = param_config['type']
        
        # Get the current value from loaded data or use empty/default
        actual_value = ""
        if section_key in self.config_data and param_key in self.config_data[section_key]:
            actual_value = self.config_data[section_key][param_key]
            logging.info(f"Using actual value for [{section_key}] {param_key}: '{actual_value}'")
        else:
            logging.info(f"No value found for [{section_key}] {param_key}, using default")
        
        if param_type == 'text':
            # Create text entry with virtual keyboard support
            entry_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            entry_box.set_halign(Gtk.Align.END)
            entry_box.set_hexpand(False)
            
            # Use standard Gtk.Entry with actual current value
            entry = Gtk.Entry()
            entry.set_text(str(actual_value) if actual_value else "")
            entry.set_size_request(200, -1)
            entry.connect("changed", self.on_text_changed, section_key, param_key)
            
            # Add button to manually show keyboard
            keyboard_btn = self._gtk.Button("keyboard", style="main_menu_production")
            keyboard_btn.set_size_request(40, -1)
            keyboard_btn.connect("clicked", self.on_keyboard_button_clicked, entry)
            
            entry_box.add(entry)
            entry_box.add(keyboard_btn)
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
            
            # Keyboard button for numeric entry
            keyboard_btn = self._gtk.Button("keyboard", style="main_menu_production")
            keyboard_btn.set_size_request(40, 50)
            keyboard_btn.connect("clicked", self.on_keyboard_button_clicked, entry)
            
            # Increase button
            increase_btn = self._gtk.Button("plus", style="background_color")
            increase_btn.set_size_request(50, 50)
            increase_btn.connect("clicked", self.on_number_changed, section_key, param_key, param_config.get('step', 1))
            
            value_box.add(decrease_btn)
            value_box.add(entry)
            value_box.add(keyboard_btn)
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
            # Create True/False buttons reflecting actual current value
            value_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            value_box.set_halign(Gtk.Align.END)
            value_box.set_hexpand(False)
            
            # False button
            false_btn = Gtk.Button("False")
            false_btn.set_size_request(80, 50)
            false_btn.connect("clicked", self.on_boolean_changed, section_key, param_key, "False")
            
            # True button
            true_btn = Gtk.Button("True")
            true_btn.set_size_request(80, 50)
            true_btn.connect("clicked", self.on_boolean_changed, section_key, param_key, "True")
            
            value_box.add(false_btn)
            value_box.add(true_btn)
            row_box.add(value_box)
            
            # Store both buttons for color management
            self.config_widgets[section_key][param_key] = {
                'true_btn': true_btn,
                'false_btn': false_btn,
                'current_value': str(actual_value).lower() if actual_value else "false"
            }
            
            # Set initial button colors based on actual current value
            bool_value = str(actual_value).lower() if actual_value else "false"
            self.update_boolean_buttons(section_key, param_key, bool_value)
            
        elif param_type == 'dropdown':
            # Create dropdown with actual current value selected
            combo_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
            combo_box.set_halign(Gtk.Align.END)
            combo_box.set_hexpand(False)
            
            combo = Gtk.ComboBoxText()
            combo.set_size_request(200, -1)
            for option in param_config['options']:
                combo.append_text(option)
                if option == str(actual_value):
                    combo.set_active_id(option)
            combo.connect("changed", self.on_dropdown_changed, section_key, param_key)
            
            combo_box.add(combo)
            row_box.add(combo_box)
            self.config_widgets[section_key][param_key] = combo

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

    def on_keyboard_button_clicked(self, button, entry):
        """Handle keyboard button click to show virtual keyboard"""
        try:
            # Focus the entry first
            entry.grab_focus()
            
            # Try multiple methods to show keyboard
            if hasattr(self._screen, 'show_keyboard'):
                self._screen.show_keyboard(entry)
                logging.info("Keyboard shown via _screen.show_keyboard")
            elif hasattr(self._screen, '_show_keyboard'):
                self._screen._show_keyboard(entry)
                logging.info("Keyboard shown via _screen._show_keyboard")
            elif hasattr(self._screen.base_panel, 'show_keyboard'):
                self._screen.base_panel.show_keyboard(entry)
                logging.info("Keyboard shown via base_panel.show_keyboard")
            # Try the gtk overlay method
            elif hasattr(self._gtk, 'show_keyboard'):
                self._gtk.show_keyboard(entry)
                logging.info("Keyboard shown via _gtk.show_keyboard")
            else:
                # Create a simple text input dialog as fallback
                self.show_text_input_dialog(entry)
                logging.info("Used fallback text input dialog")
        except Exception as e:
            logging.error(f"Could not show virtual keyboard: {e}")
            # Last resort: create input dialog
            self.show_text_input_dialog(entry)

    def show_text_input_dialog(self, entry):
        """Show a simple text input dialog as keyboard fallback"""
        try:
            dialog = Gtk.MessageDialog(
                parent=self._screen,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text=_("Enter Value")
            )
            
            content_area = dialog.get_content_area()
            input_entry = Gtk.Entry()
            input_entry.set_text(entry.get_text())
            input_entry.set_size_request(300, -1)
            content_area.add(input_entry)
            
            dialog.show_all()
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                entry.set_text(input_entry.get_text())
                # Trigger the changed signal manually
                entry.emit("changed")
                
            dialog.destroy()
            
        except Exception as e:
            logging.error(f"Failed to show text input dialog: {e}")

    def on_entry_focus_in(self, entry, event):
        """Handle entry focus in - show virtual keyboard"""
        try:
            # Show virtual keyboard for text input using KlipperScreen's method
            if hasattr(self._screen, '_show_keyboard'):
                self._screen._show_keyboard(entry)
            elif hasattr(self._screen, 'show_keyboard'):
                self._screen.show_keyboard(entry)
            elif hasattr(self._screen, 'base_panel') and hasattr(self._screen.base_panel, 'show_keyboard'):
                self._screen.base_panel.show_keyboard(entry)
        except Exception as e:
            logging.debug(f"Could not show virtual keyboard: {e}")
        return False

    def on_entry_focus_out(self, entry, event):
        """Handle entry focus out - hide virtual keyboard"""
        try:
            # Hide virtual keyboard using KlipperScreen's method
            if hasattr(self._screen, '_hide_keyboard'):
                self._screen._hide_keyboard()
            elif hasattr(self._screen, 'hide_keyboard'):
                self._screen.hide_keyboard()
            elif hasattr(self._screen, 'base_panel') and hasattr(self._screen.base_panel, 'hide_keyboard'):
                self._screen.base_panel.hide_keyboard()
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
        """Load current printer configuration from Klipper"""
        try:
            # Use the same method that works for saving - download the file directly
            import threading
            threading.Thread(target=self._load_config_from_file_async).start()
            logging.info("Loading configuration from file...")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            self._screen.show_popup_message(_("Failed to load printer configuration"))

    def _load_config_from_file_async(self):
        """Load configuration directly from printer.cfg file"""
        try:
            import requests
            
            # Download the printer.cfg file using the same method as saving
            download_url = f"{self._screen.apiclient.endpoint}/server/files/config/printer.cfg"
            logging.info(f"Downloading config from {download_url}")
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                config_text = response.text
                logging.info("Config file downloaded successfully for loading")
                
                # Parse the configuration to extract current values
                self._parse_config_file(config_text)
            else:
                error_msg = f"Failed to download config file: HTTP {response.status_code}"
                logging.error(error_msg)
                GLib.idle_add(self._screen.show_popup_message, _("Failed to load configuration"))
                
        except Exception as e:
            logging.error(f"Config loading exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
            GLib.idle_add(self._screen.show_popup_message, _("Failed to load configuration"))

    def _parse_config_file(self, config_text: str):
        """Parse the printer.cfg file to extract current values"""
        import re
        
        self.config_data = {}
        lines = config_text.split('\n')
        current_section = None
        
        logging.info("Parsing printer.cfg file...")
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check if this is a section header like [printer] or [stepper_x]
            section_match = re.match(r'^\[([^\]]+)\]', line_stripped)
            if section_match:
                current_section = section_match.group(1)
                # Only initialize sections we care about
                if current_section in self.config_sections:
                    self.config_data[current_section] = {}
                    logging.info(f"Found section: {current_section}")
                continue
            
            # Check if this is a parameter line like "max_velocity: 100" or "kinematics = cartesian"
            param_match = re.match(r'^([^#:=]+)[:=]\s*(.*)$', line_stripped)
            if param_match and current_section and current_section in self.config_sections:
                param_name = param_match.group(1).strip()
                param_value = param_match.group(2).strip()
                
                # Only store parameters that are defined in our UI
                if param_name in self.config_sections[current_section]['params']:
                    self.config_data[current_section][param_name] = param_value
                    logging.info(f"Loaded [{current_section}] {param_name} = {param_value}")
        
        # Initialize empty sections for missing ones
        for section_name in self.config_sections.keys():
            if section_name not in self.config_data:
                self.config_data[section_name] = {}
                logging.info(f"Initialized empty section: {section_name}")
                
        logging.info(f"Configuration parsing completed. Found sections: {list(self.config_data.keys())}")
        
        # Update the widgets on the main thread
        GLib.idle_add(self.update_widgets)

    def _on_config_received(self, result):
        """Process received configuration data (fallback method)"""
        logging.warning("Using fallback API method - this might not work properly")
        if "error" in result:
            logging.error(f"Config error: {result['error']}")
            return
            
        try:
            # The result should contain the configuration sections
            query_result = result.get("result", {})
            status = query_result.get("status", {})
            configfile = status.get("configfile", {})
            config_data = configfile.get("config", {})
            
            self.config_data = {}
            
            # Parse the configuration data for known sections
            for section_name in self.config_sections.keys():
                if section_name in config_data:
                    self.config_data[section_name] = dict(config_data[section_name])
                    # Remove any parameters not in our UI definition
                    section_params = self.config_sections[section_name]['params']
                    filtered_data = {}
                    for param_key in section_params.keys():
                        if param_key in self.config_data[section_name]:
                            filtered_data[param_key] = self.config_data[section_name][param_key]
                    self.config_data[section_name] = filtered_data
                else:
                    # Initialize empty section if it doesn't exist
                    self.config_data[section_name] = {}
                    
            logging.info(f"Configuration data loaded successfully: {list(self.config_data.keys())}")
            logging.debug(f"Config data: {self.config_data}")
            GLib.idle_add(self.update_widgets)
            
        except Exception as e:
            logging.error(f"Failed to parse config data: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def update_widgets(self):
        """Update widgets with loaded configuration data"""
        logging.info("=== UPDATING WIDGETS ===")
        logging.info(f"Available config sections: {list(self.config_data.keys())}")
        
        for section_key, section_data in self.config_data.items():
            logging.info(f"Section '{section_key}' has data: {section_data}")
            
            if section_key in self.config_widgets:
                logging.info(f"Found widgets for section '{section_key}'")
                for param_key, value in section_data.items():
                    if param_key in self.config_widgets[section_key]:
                        widget = self.config_widgets[section_key][param_key]
                        logging.info(f"Updating [{section_key}] {param_key} with value '{value}'")
                        
                        if isinstance(widget, Gtk.Entry):
                            # Text widget - update with current value
                            widget.set_text(str(value) if value else "")
                            logging.info(f"✅ Set text field to: '{value}'")
                        elif isinstance(widget, Gtk.ComboBoxText):
                            # Dropdown widget - select current value
                            widget.set_active_id(str(value) if value else "")
                            logging.info(f"✅ Set dropdown to: '{value}'")
                        elif isinstance(widget, dict):
                            if 'entry' in widget:
                                # Number/decimal widget - update entry with current value
                                display_value = str(value) if value else "0"
                                widget['entry'].set_text(display_value)
                                logging.info(f"✅ Set number entry to: '{display_value}'")
                            elif 'true_btn' in widget and 'false_btn' in widget:
                                # Boolean widget - update button colors based on current value
                                bool_value = str(value).lower() if value else "false"
                                self.update_boolean_buttons(section_key, param_key, bool_value)
                                logging.info(f"✅ Set boolean buttons to: '{bool_value}'")
                    else:
                        logging.warning(f"❌ No widget found for [{section_key}] {param_key}")
            else:
                logging.warning(f"❌ No widget section found for '{section_key}'")
                
        logging.info("=== WIDGET UPDATE COMPLETED ===")
        
        # Show a confirmation message
        GLib.idle_add(self._screen.show_popup_message, _("Configuration loaded successfully"))

    def save_config(self, widget):
        """Save configuration changes to printer.cfg"""
        try:
            # First, download the current printer.cfg file
            self._screen.show_popup_message(_("Loading current configuration..."))
            
            # Use REST API to download the current file first
            import threading
            threading.Thread(target=self._save_config_async).start()
            
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            self._screen.show_popup_message(_("Failed to save configuration"))

    def _save_config_async(self):
        """Save configuration asynchronously using REST API"""
        try:
            import requests
            
            # First, download the current printer.cfg file
            download_url = f"{self._screen.apiclient.endpoint}/server/files/config/printer.cfg"
            
            logging.info(f"Downloading current config from {download_url}")
            
            # Download current file
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                current_config = response.text
                logging.info("Current config downloaded successfully")
                
                # Modify the configuration with new values
                modified_config = self.modify_existing_config(current_config)
                
                # Upload the modified file
                self.upload_modified_config(modified_config)
            else:
                error_msg = f"Failed to download current config: HTTP {response.status_code}"
                logging.error(error_msg)
                GLib.idle_add(self._on_config_saved_error, error_msg)
                
        except Exception as e:
            logging.error(f"Save exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
            GLib.idle_add(self._on_config_saved_error, str(e))

    def modify_existing_config(self, config_text: str) -> str:
        """Modify the existing configuration with new values"""
        import re
        
        lines = config_text.split('\n')
        modified_lines = []
        current_section = None
        
        for line in lines:
            # Check if this is a section header
            section_match = re.match(r'^\[([^\]]+)\]', line.strip())
            if section_match:
                current_section = section_match.group(1)
                modified_lines.append(line)
                continue
            
            # Check if this is a parameter line
            param_match = re.match(r'^([^#:=]+)[:=]\s*(.*)$', line.strip())
            if param_match and current_section:
                param_name = param_match.group(1).strip()
                original_value = param_match.group(2).strip()
                
                # Check if we have a new value for this parameter
                if (current_section in self.config_data and 
                    param_name in self.config_data[current_section]):
                    
                    new_value = self.config_data[current_section][param_name]
                    # Preserve the original format (: or =)
                    separator = ':' if ':' in line else '='
                    # Preserve indentation
                    leading_space = len(line) - len(line.lstrip())
                    indent = ' ' * leading_space
                    modified_line = f"{indent}{param_name}{separator} {new_value}"
                    
                    logging.info(f"Modified [{current_section}] {param_name}: {original_value} -> {new_value}")
                    modified_lines.append(modified_line)
                else:
                    # Keep original line
                    modified_lines.append(line)
            else:
                # Keep original line (comments, empty lines, etc.)
                modified_lines.append(line)
        
        return '\n'.join(modified_lines)

    def upload_modified_config(self, config_content: str):
        """Upload the modified configuration"""
        try:
            import requests
            
            # Use the existing API client from KlipperScreen
            url = f"{self._screen.apiclient.endpoint}/server/files/upload"
            
            # Prepare the file data as bytes
            file_content = config_content.encode('utf-8')
            
            # Use multipart form data
            files = {
                'file': ('printer.cfg', file_content, 'text/plain')
            }
            data = {
                'root': 'config'
            }
            
            logging.info(f"Uploading modified config to {url}")
            logging.debug(f"Modified config preview: {config_content[:500]}...")
            
            # Make the request
            response = requests.post(url, files=files, data=data, timeout=30)
            
            logging.info(f"Upload response: {response.status_code} - {response.text}")
            
            if response.status_code in [200, 201]:
                GLib.idle_add(self._on_config_saved_success)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                GLib.idle_add(self._on_config_saved_error, error_msg)
                
        except Exception as e:
            logging.error(f"Upload exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
            GLib.idle_add(self._on_config_saved_error, str(e))

    def _on_config_saved_success(self):
        """Handle successful config save"""
        logging.info("Configuration saved successfully")
        
        # Show success message with restart option
        def restart_klipper(widget):
            self._screen._ws.klippy.restart_firmware()
            self._screen.show_popup_message(_("Klipper is restarting..."))
        
        # Create a dialog with restart button
        dialog = Gtk.MessageDialog(
            parent=self._screen,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text=_("Configuration saved successfully!")
        )
        dialog.format_secondary_text(_("Do you want to restart Klipper to apply the changes?"))
        
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        restart_btn = dialog.add_button(_("Restart Klipper"), Gtk.ResponseType.OK)
        restart_btn.get_style_context().add_class("color1")
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            restart_klipper(None)

    def _on_config_saved_error(self, error_msg):
        """Handle config save error"""
        logging.error(f"Save error: {error_msg}")
        self._screen.show_popup_message(_("Failed to save configuration: ") + str(error_msg))

    def reload_config(self, widget):
        """Reload configuration from the printer"""
        self.load_config_data()
        self._screen.show_popup_message(_("Configuration reloaded"))

    def activate(self):
        """Called when the panel is activated"""
        self.load_config_data()

    def deactivate(self):
        """Called when the panel is deactivated"""
        pass