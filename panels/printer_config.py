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
        
        # List of configuration sections to display (easily modifiable)
        # Add or remove section names here to customize what appears in the UI
        self.allowed_sections = [
            'printer',
            'stepper_x', 
            'stepper_y',
            'stepper_z',
            'extruder',
            'extruder1',
            'gcode_macro T0',
            'gcode_macro T1'
        ]
        
        # Parameter type definitions with validation rules
        # These will be applied automatically when parameters are found
        self.parameter_types = {
            # Printer section parameters
            'kinematics': {'type': 'text', 'name': _('Kinematics')},
            'max_velocity': {'type': 'number', 'name': _('Max Velocity'), 'min': 10, 'max': 1000, 'step': 10},
            'max_accel': {'type': 'number', 'name': _('Max Acceleration'), 'min': 10, 'max': 10000, 'step': 10},
            'max_z_velocity': {'type': 'number', 'name': _('Max Z Velocity'), 'min': 1, 'max': 100, 'step': 1},
            'max_z_accel': {'type': 'number', 'name': _('Max Z Acceleration'), 'min': 10, 'max': 1000, 'step': 10},
            
            # Stepper parameters
            'step_pin': {'type': 'text', 'name': _('Step Pin')},
            'dir_pin': {'type': 'text', 'name': _('Direction Pin')},
            'enable_pin': {'type': 'text', 'name': _('Enable Pin')},
            'microsteps': {'type': 'number', 'name': _('Microsteps'), 'min': 1, 'max': 256, 'step': 1},
            'rotation_distance': {'type': 'decimal', 'name': _('Rotation Distance'), 'min': 0.1, 'max': 1000, 'step': 0.1},
            'endstop_pin': {'type': 'text', 'name': _('Endstop Pin')},
            'position_endstop': {'type': 'decimal', 'name': _('Position Endstop'), 'min': -100000, 'max': 100000, 'step': 0.1},
            'position_max': {'type': 'decimal', 'name': _('Position Max'), 'min': 1, 'max': 100000, 'step': 0.1},
            'position_min': {'type': 'decimal', 'name': _('Position Min'), 'min': -100000, 'max': 100000, 'step': 0.1},
            'homing_speed': {'type': 'number', 'name': _('Homing Speed'), 'min': 1, 'max': 200, 'step': 5},
            'homing_retract_dist': {'type': 'number', 'name': _('Homing Retract Distance'), 'min': 1, 'max': 50, 'step': 1},
            'homing_positive_dir': {'type': 'boolean', 'name': _('Homing Positive Direction')},
            
            # Extruder parameters
            'nozzle_diameter': {'type': 'decimal', 'name': _('Nozzle Diameter'), 'min': 0.1, 'max': 20.0, 'step': 0.1},
            'filament_diameter': {'type': 'decimal', 'name': _('Filament Diameter'), 'min': 0.1, 'max': 20.0, 'step': 0.1},
            'heater_pin': {'type': 'text', 'name': _('Heater Pin')},
            'sensor_type': {'type': 'text', 'name': _('Sensor Type')},
            'sensor_pin': {'type': 'text', 'name': _('Sensor Pin')},
            'control': {'type': 'text', 'name': _('Control')},
            'pid_Kp': {'type': 'decimal', 'name': _('PID Kp'), 'min': 0.1, 'max': 1000, 'step': 0.1},
            'pid_Ki': {'type': 'decimal', 'name': _('PID Ki'), 'min': 0.01, 'max': 100, 'step': 0.01},
            'pid_Kd': {'type': 'decimal', 'name': _('PID Kd'), 'min': 1, 'max': 10000, 'step': 1},
            'max_temp': {'type': 'number', 'name': _('Max Temperature'), 'min': 50, 'max': 50000, 'step': 5},
            'min_temp': {'type': 'number', 'name': _('Min Temperature'), 'min': -300, 'max': 100, 'step': 5},
            'min_extrude_temp': {'type': 'number', 'name': _('Min Extrude Temp'), 'min': -300, 'max': 300, 'step': 5},
            'max_extrude_only_distance': {'type': 'number', 'name': _('Max Extrude Distance'), 'min': 50, 'max': 50000000, 'step': 100},
            'max_extrude_cross_section': {'type': 'number', 'name': _('Max Cross Section'), 'min': 50, 'max': 50000000, 'step': 100},
            
            # TMC driver parameters
            'cs_pin': {'type': 'text', 'name': _('CS Pin')},
            'spi_bus': {'type': 'text', 'name': _('SPI Bus')},
            'spi_speed': {'type': 'number', 'name': _('SPI Speed'), 'min': 100000, 'max': 10000000, 'step': 100000},
            'run_current': {'type': 'decimal', 'name': _('Run Current'), 'min': 0.1, 'max': 5.0, 'step': 0.1},
            'interpolate': {'type': 'boolean', 'name': _('Interpolate')},
            
            # Gcode macro parameters
            'gcode': {'type': 'text', 'name': _('Gcode'), 'multiline': True},
            'description': {'type': 'text', 'name': _('Description')},
            
            # Common parameters that might appear in various sections
            'extruder': {'type': 'text', 'name': _('Extruder')},
            'serial': {'type': 'text', 'name': _('Serial')},
            'pin': {'type': 'text', 'name': _('Pin')},
            'value': {'type': 'decimal', 'name': _('Value'), 'min': -1000000, 'max': 1000000, 'step': 0.1}
        }
        
        # Dynamic configuration sections - will be populated from actual config file
        self.config_sections = {}
        
        self.create_main_menu()
        self.load_config_data()

    def get_section_display_name(self, section_name: str) -> str:
        """Generate a user-friendly display name for a section"""
        # Convert section names to readable format
        name_mapping = {
            'printer': _('Printer Settings'),
            'stepper_x': _('X Stepper'),
            'stepper_y': _('Y Stepper'), 
            'stepper_z': _('Z Stepper'),
            'stepper_z1': _('Z1 Stepper'),
            'extruder': _('Extruder'),
            'extruder1': _('Extruder 1'),
            'gcode_macro T0': _('Gcode Macro T0'),
            'gcode_macro T1': _('Gcode Macro T1')
        }
        
        # Check if we have a predefined name
        if section_name in name_mapping:
            return name_mapping[section_name]
        
        # Generate name from section name
        if section_name.startswith('gcode_macro'):
            macro_name = section_name.replace('gcode_macro ', '')
            return f"{_('Gcode Macro')} {macro_name}"
        elif section_name.startswith('tmc'):
            parts = section_name.split(' ')
            if len(parts) >= 2:
                return f"{parts[0].upper()} {parts[1].replace('_', ' ').title()}"
        
        # Default: capitalize and replace underscores
        return section_name.replace('_', ' ').title()

    def get_parameter_config(self, param_name: str) -> Dict[str, Any]:
        """Get parameter configuration with automatic type detection"""
        # Check if we have a predefined config for this parameter
        if param_name in self.parameter_types:
            return self.parameter_types[param_name].copy()
        
        # Auto-detect parameter type based on name patterns
        param_lower = param_name.lower()
        
        # Boolean parameters
        if any(keyword in param_lower for keyword in ['enable', 'interpolate', 'invert', 'positive_dir']):
            return {'type': 'boolean', 'name': _(param_name.replace('_', ' ').title())}
        
        # Pin parameters
        if 'pin' in param_lower:
            return {'type': 'text', 'name': _(param_name.replace('_', ' ').title())}
        
        # Temperature parameters
        if 'temp' in param_lower:
            return {'type': 'number', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': -300, 'max': 50000, 'step': 5}
        
        # Speed/velocity parameters
        if any(keyword in param_lower for keyword in ['speed', 'velocity', 'accel']):
            return {'type': 'number', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': 1, 'max': 10000, 'step': 1}
        
        # Distance/position parameters
        if any(keyword in param_lower for keyword in ['distance', 'position', 'diameter']):
            return {'type': 'decimal', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': -100000, 'max': 100000, 'step': 0.1}
        
        # Current parameters
        if 'current' in param_lower:
            return {'type': 'decimal', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': 0.1, 'max': 5.0, 'step': 0.1}
        
        # PID parameters
        if param_lower.startswith('pid_'):
            return {'type': 'decimal', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': 0.01, 'max': 10000, 'step': 0.01}
        
        # Microsteps
        if 'microsteps' in param_lower:
            return {'type': 'number', 'name': _(param_name.replace('_', ' ').title()), 
                   'min': 1, 'max': 256, 'step': 1}
        
        # Default to text for unknown parameters
        return {'type': 'text', 'name': _(param_name.replace('_', ' ').title())}

    def create_main_menu(self):
        """Create the main configuration menu with section buttons"""
        self.labels['config_menu'] = self._gtk.ScrolledWindow()
        self.labels['config'] = Gtk.Grid()
        self.labels['config_menu'].add(self.labels['config'])
        
        # Add save and reload buttons FIRST (at the top)
        self.add_action_buttons()
        
        # Content will be added after config is loaded
        self.content.add(self.labels['config_menu'])

    def populate_main_menu(self):
        """Populate the main menu with available sections"""
        # Add sections as menu items AFTER the action buttons
        for section_key in self.config_sections.keys():
            self.add_section_option(section_key)

    def add_section_option(self, section_key: str):
        """Add a section option to the main menu"""
        section_name = self.get_section_display_name(section_key)
        
        name = Gtk.Label(
            hexpand=True, vexpand=True, halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
            wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0)
        name.set_markup(f"<big><b>{section_name}</b></big>")

        row_box = Gtk.Box(spacing=5, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        row_box.get_style_context().add_class("frame-item")
        row_box.add(name)

        open_section = self._gtk.Button("settings", style="main_menu_control")
        open_section.connect("clicked", self.load_section_menu, section_key, section_name)
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

        # Add save button at row 0
        self.labels['config'].insert_row(0)
        self.labels['config'].attach(save_row, 0, 0, 1, 1)
        
        # Add reload button at row 1
        self.labels['config'].insert_row(1)
        self.labels['config'].attach(reload_row, 0, 1, 1, 1)

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
            # Check if this is a multiline text field (like gcode)
            is_multiline = param_config.get('multiline', False)
            
            if is_multiline:
                # Create a text view with scroll for multiline content
                text_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.VERTICAL)
                text_box.set_halign(Gtk.Align.END)
                text_box.set_hexpand(False)
                
                # Create scrolled window for text view
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                scrolled.set_size_request(300, 150)
                
                # Create text view
                text_view = Gtk.TextView()
                text_view.set_wrap_mode(Gtk.WrapMode.WORD)
                text_view.get_buffer().set_text(str(actual_value) if actual_value else "")
                text_view.get_buffer().connect("changed", self.on_text_view_changed, section_key, param_key)
                
                scrolled.add(text_view)
                
                # Add button for virtual keyboard
                keyboard_btn = self._gtk.Button("keyboard", style="main_menu_production")
                keyboard_btn.set_size_request(40, -1)
                keyboard_btn.connect("clicked", self.on_keyboard_button_clicked_textview, text_view)
                
                button_box = Gtk.Box(spacing=5, orientation=Gtk.Orientation.HORIZONTAL)
                button_box.set_halign(Gtk.Align.END)
                button_box.add(keyboard_btn)
                
                text_box.add(scrolled)
                text_box.add(button_box)
                row_box.add(text_box)
                self.config_widgets[section_key][param_key] = text_view
            else:
                # Create single-line text entry with virtual keyboard support
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

        return row_box

    def on_text_changed(self, entry, section_key: str, param_key: str):
        """Handle text entry changes"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
        self.config_data[section_key][param_key] = entry.get_text()

    def on_text_view_changed(self, text_buffer, section_key: str, param_key: str):
        """Handle text view changes for multiline content"""
        if section_key not in self.config_data:
            self.config_data[section_key] = {}
        start_iter = text_buffer.get_start_iter()
        end_iter = text_buffer.get_end_iter()
        text_content = text_buffer.get_text(start_iter, end_iter, False)
        self.config_data[section_key][param_key] = text_content

    def on_keyboard_button_clicked_textview(self, button, text_view):
        """Handle keyboard button click for text view to show virtual keyboard"""
        try:
            # Get the text buffer
            text_buffer = text_view.get_buffer()
            start_iter = text_buffer.get_start_iter()
            end_iter = text_buffer.get_end_iter()
            current_text = text_buffer.get_text(start_iter, end_iter, False)
            
            # Show text input dialog
            self.show_text_input_dialog_for_textview(text_view, current_text)
        except Exception as e:
            logging.error(f"Keyboard button error for text view: {e}")

    def show_text_input_dialog_for_textview(self, text_view, current_text):
        """Show a text input dialog for text view with multiline support"""
        try:
            dialog = Gtk.Dialog(
                title=_("Edit Text"),
                parent=self._screen,
                flags=0
            )
            dialog.set_default_size(500, 400)
            
            # Create text view for the dialog
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            
            dialog_text_view = Gtk.TextView()
            dialog_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
            dialog_text_view.get_buffer().set_text(current_text)
            
            scrolled.add(dialog_text_view)
            dialog.get_content_area().add(scrolled)
            
            # Add buttons
            dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            ok_button = dialog.add_button(_("OK"), Gtk.ResponseType.OK)
            ok_button.get_style_context().add_class("color1")
            
            dialog.show_all()
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                # Get the text from dialog and set it to the original text view
                dialog_buffer = dialog_text_view.get_buffer()
                start_iter = dialog_buffer.get_start_iter()
                end_iter = dialog_buffer.get_end_iter()
                new_text = dialog_buffer.get_text(start_iter, end_iter, False)
                text_view.get_buffer().set_text(new_text)
            
            dialog.destroy()
        except Exception as e:
            logging.error(f"Text input dialog error: {e}")

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
                text=_("Enter value:")
            )
            
            # Add an entry to the dialog
            content_area = dialog.get_content_area()
            dialog_entry = Gtk.Entry()
            dialog_entry.set_text(entry.get_text())
            content_area.add(dialog_entry)
            dialog.show_all()
            
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                entry.set_text(dialog_entry.get_text())
            
            dialog.destroy()
        except Exception as e:
            logging.error(f"Text input dialog error: {e}")

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
        """Parse the printer.cfg file to extract current values and build sections dynamically"""
        self.config_data = {}
        self.config_sections = {}
        lines = config_text.split('\n')
        current_section = None
        collecting_gcode = False
        gcode_lines = []
        
        logging.info("Parsing printer.cfg file...")
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines and standalone comments
            if not line_stripped or line_stripped.startswith('#'):
                if collecting_gcode:
                    # Include empty lines in gcode blocks
                    gcode_lines.append(line)
                continue
            
            # Check if this is a section header like [printer] or [stepper_x]
            section_match = re.match(r'^\[([^\]]+)\]', line_stripped)
            if section_match:
                # If we were collecting gcode, save it first
                if collecting_gcode and current_section:
                    if current_section in self.config_data:
                        self.config_data[current_section]['gcode'] = '\n'.join(gcode_lines).strip()
                    collecting_gcode = False
                    gcode_lines = []
                
                current_section = section_match.group(1)
                
                # Check if this section is in our allowed list
                if current_section in self.allowed_sections:
                    self.config_data[current_section] = {}
                    self.config_sections[current_section] = {
                        'name': self.get_section_display_name(current_section),
                        'params': {}
                    }
                    logging.info(f"Found allowed section: {current_section}")
                continue
            
            # Handle gcode macro content (special case for multi-line gcode)
            if (current_section and current_section.startswith('gcode_macro') and 
                current_section in self.allowed_sections):
                if line_stripped.lower() == 'gcode:':
                    collecting_gcode = True
                    gcode_lines = []
                    continue
                elif collecting_gcode:
                    # Add line to gcode content, preserving original formatting
                    gcode_lines.append(line)
                    continue
            
            # Check if this is a parameter line like "max_velocity: 100" or "kinematics = cartesian"
            param_match = re.match(r'^([^#:=]+)[:=]\s*(.*)$', line_stripped)
            if param_match and current_section and current_section in self.allowed_sections:
                param_name = param_match.group(1).strip()
                param_value = param_match.group(2).strip()
                
                # Remove inline comments from value
                if '#' in param_value:
                    param_value = param_value.split('#')[0].strip()
                
                # Store the parameter value
                self.config_data[current_section][param_name] = param_value
                
                # Add parameter to section config with auto-detected type
                param_config = self.get_parameter_config(param_name)
                self.config_sections[current_section]['params'][param_name] = param_config
                
                logging.info(f"Added parameter [{current_section}] {param_name} = '{param_value}'")
        
        # Handle any remaining gcode content at end of file
        if collecting_gcode and current_section and current_section in self.config_data:
            self.config_data[current_section]['gcode'] = '\n'.join(gcode_lines).strip()
        
        logging.info(f"Configuration parsing completed. Found sections: {list(self.config_data.keys())}")
        
        # Update the UI on the main thread
        GLib.idle_add(self.populate_main_menu)
        GLib.idle_add(self.update_widgets)

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
                        elif isinstance(widget, Gtk.TextView):
                            # Text view widget for multiline content - update with current value
                            widget.get_buffer().set_text(str(value) if value else "")
                            logging.info(f"✅ Set text view to: '{value}'")
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
            logging.error(f"Save error: {e}")
            self._screen.show_popup_message(_("Failed to save configuration"))

    def _save_config_async(self):
        """Save configuration asynchronously using REST API"""
        try:
            import requests
            
            # First download the current config file
            download_url = f"{self._screen.apiclient.endpoint}/server/files/config/printer.cfg"
            logging.info(f"Downloading current config from {download_url}")
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                current_config = response.text
                logging.info("Current config downloaded successfully")
                
                # Modify the configuration with our changes
                modified_config = self.modify_existing_config(current_config)
                
                # Upload the modified configuration
                self.upload_modified_config(modified_config)
            else:
                error_msg = f"Failed to download current config: HTTP {response.status_code}"
                logging.error(error_msg)
                GLib.idle_add(self._screen.show_popup_message, _("Failed to save configuration"))
                
        except Exception as e:
            logging.error(f"Save config exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
            GLib.idle_add(self._screen.show_popup_message, _("Failed to save configuration"))

    def modify_existing_config(self, config_text: str) -> str:
        """Modify the existing configuration with new values"""
        lines = config_text.split('\n')
        modified_lines = []
        current_section = None
        in_gcode_block = False
        skip_until_next_section = False
        
        for line in lines:
            # Check if this is a section header
            section_match = re.match(r'^\[([^\]]+)\]', line.strip())
            if section_match:
                current_section = section_match.group(1)
                in_gcode_block = False
                skip_until_next_section = False
                modified_lines.append(line)
                continue
            
            # Handle gcode macro sections specially
            if current_section and current_section.startswith('gcode_macro'):
                if line.strip().lower() == 'gcode:':
                    # Start of gcode block
                    in_gcode_block = True
                    skip_until_next_section = True
                    modified_lines.append(line)
                    
                    # Add our new gcode content if we have it
                    if (current_section in self.config_data and 
                        'gcode' in self.config_data[current_section]):
                        new_gcode = self.config_data[current_section]['gcode']
                        if new_gcode:
                            # Add each line with proper indentation
                            for gcode_line in new_gcode.split('\n'):
                                if gcode_line.strip():
                                    modified_lines.append(f"  {gcode_line}")
                                else:
                                    modified_lines.append("")
                    continue
                elif in_gcode_block and skip_until_next_section:
                    # Skip original gcode content, we already added our new content
                    continue
            
            # Skip if we're in a gcode block that we're replacing
            if skip_until_next_section and not section_match:
                continue
            
            # Check if this is a parameter line
            param_match = re.match(r'^([^#:=]+)[:=]\s*(.*)$', line.strip())
            if param_match and current_section and not in_gcode_block:
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
                'root': 'config',
                'path': ''
            }
            
            logging.info("Uploading modified configuration...")
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 201:
                logging.info("Configuration uploaded successfully")
                GLib.idle_add(self._on_config_saved_success)
            else:
                error_msg = f"Upload failed: HTTP {response.status_code} - {response.text}"
                logging.error(error_msg)
                GLib.idle_add(self._on_config_saved_error, error_msg)
                
        except Exception as e:
            error_msg = f"Upload exception: {e}"
            logging.error(error_msg)
            GLib.idle_add(self._on_config_saved_error, error_msg)

    def _on_config_saved_success(self):
        """Handle successful config save"""
        logging.info("Configuration saved successfully")
        
        # Show success message with restart option
        def restart_klipper(widget):
            try:
                # Send restart command to Klipper
                self._screen._ws.klippy.restart()
                logging.info("Klipper restart initiated")
            except Exception as e:
                logging.error(f"Failed to restart Klipper: {e}")
        
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