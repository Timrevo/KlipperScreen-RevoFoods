import logging
import os
import json
from datetime import datetime, timedelta
import calendar

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or _("Print Statistics")
        super().__init__(screen, title)
        self.history_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'history.json')
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_homogeneous(False)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<span size='large' weight='bold'>Print Statistics</span>")
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.pack_start(title_label, False, False, 10)
        
        # Create scrollable area that contains EVERYTHING (statistics + button)
        scroll = self._gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Statistics container that will contain stats AND button
        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.add(self.stats_box)
        
        # The scroll takes ALL the remaining space
        main_box.pack_start(scroll, True, True, 0)
        
        self.content.add(main_box)
        self.load_statistics()

    def load_history_data(self):
        """Load print history from JSON file"""
        try:
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            logging.error(f"Error loading history data: {e}")
            return {}

    def calculate_statistics(self, file_data):
        """Calculate print statistics for a file"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        daily_count = 0
        weekly_count = 0
        monthly_count = 0
        total_count = 0
        
        for date_str, count in file_data.items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                total_count += count
                
                # Daily count
                if date_obj == today:
                    daily_count += count
                
                # Weekly count
                if date_obj >= week_start:
                    weekly_count += count
                
                # Monthly count
                if date_obj >= month_start:
                    monthly_count += count
                    
            except ValueError:
                logging.warning(f"Invalid date format in history: {date_str}")
                continue
        
        return {
            'daily': daily_count,
            'weekly': weekly_count,
            'monthly': monthly_count,
            'total': total_count
        }

    def create_file_statistics_widget(self, filename, stats):
        """Create a widget showing statistics for a single file"""
        # Main frame for this file
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.set_margin_top(5)
        frame.set_margin_bottom(5)
        frame.set_margin_left(10)
        frame.set_margin_right(10)
        
        # Container for file info
        file_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        file_box.set_margin_top(10)
        file_box.set_margin_bottom(10)
        file_box.set_margin_left(15)
        file_box.set_margin_right(15)
        
        # File name (remove .gcode extension)
        display_name = filename.replace('.gcode', '') if filename.endswith('.gcode') else filename
        file_label = Gtk.Label()
        file_label.set_markup(f"<span weight='bold' size='medium'>{display_name}</span>")
        file_label.set_halign(Gtk.Align.START)
        file_label.set_ellipsize(Pango.EllipsizeMode.END)
        file_box.pack_start(file_label, False, False, 0)
        
        # Statistics grid
        stats_grid = Gtk.Grid()
        stats_grid.set_column_spacing(20)
        stats_grid.set_row_spacing(5)
        stats_grid.set_column_homogeneous(True)
        
        # Headers
        headers = ["Period", "Cycle"]
        for i, header in enumerate(headers):
            label = Gtk.Label()
            label.set_markup(f"<span weight='bold'>{header}</span>")
            label.set_halign(Gtk.Align.CENTER)
            stats_grid.attach(label, i, 0, 1, 1)
        
        # Statistics rows
        periods = [
            ("Today", stats['daily']),
            ("This Week", stats['weekly']),
            ("This Month", stats['monthly']),
            ("Total", stats['total'])
        ]
        
        for row, (period, count) in enumerate(periods, 1):
            # Period label
            period_label = Gtk.Label(period)
            period_label.set_halign(Gtk.Align.START)
            stats_grid.attach(period_label, 0, row, 1, 1)
            
            # Count label
            count_label = Gtk.Label(str(count))
            count_label.set_halign(Gtk.Align.CENTER)
            if period == "Total" and count > 0:
                count_label.set_markup(f"<span weight='bold' color='#4CAF50'>{count}</span>")
            elif count > 0:
                count_label.set_markup(f"<span color='#2196F3'>{count}</span>")
            stats_grid.attach(count_label, 1, row, 1, 1)
        
        file_box.pack_start(stats_grid, False, False, 0)
        frame.add(file_box)
        
        return frame

    def load_statistics(self):
        """Load and display print statistics"""
        # Clear existing widgets
        for child in self.stats_box.get_children():
            self.stats_box.remove(child)
        
        history_data = self.load_history_data()
        
        if not history_data:
            # No data available
            no_data_label = Gtk.Label()
            no_data_label.set_markup("<span size='large'>No print history available</span>")
            no_data_label.set_halign(Gtk.Align.CENTER)
            no_data_label.set_valign(Gtk.Align.CENTER)
            self.stats_box.pack_start(no_data_label, True, True, 20)
        else:
            # Sort files by total prints (descending)
            sorted_files = []
            for filename, file_data in history_data.items():
                stats = self.calculate_statistics(file_data)
                sorted_files.append((filename, stats))
            
            sorted_files.sort(key=lambda x: x[1]['total'], reverse=True)
            
            # Create summary statistics
            summary_frame = Gtk.Frame()
            summary_frame.set_shadow_type(Gtk.ShadowType.OUT)
            summary_frame.set_margin_top(5)
            summary_frame.set_margin_bottom(10)
            summary_frame.set_margin_left(10)
            summary_frame.set_margin_right(10)
            
            summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            summary_box.set_margin_top(10)
            summary_box.set_margin_bottom(10)
            summary_box.set_margin_left(15)
            summary_box.set_margin_right(15)
            
            summary_title = Gtk.Label()
            summary_title.set_markup("<span size='large' weight='bold'>Overall Summary</span>")
            summary_title.set_halign(Gtk.Align.CENTER)
            summary_box.pack_start(summary_title, False, False, 5)
            
            # Calculate overall statistics
            total_daily = sum(stats['daily'] for _, stats in sorted_files)
            total_weekly = sum(stats['weekly'] for _, stats in sorted_files)
            total_monthly = sum(stats['monthly'] for _, stats in sorted_files)
            total_all_time = sum(stats['total'] for _, stats in sorted_files)
            
            summary_grid = Gtk.Grid()
            summary_grid.set_column_spacing(30)
            summary_grid.set_row_spacing(5)
            summary_grid.set_halign(Gtk.Align.CENTER)
            
            summary_stats = [
                ("Today:", total_daily),
                ("This Week:", total_weekly),
                ("This Month:", total_monthly),
                ("All Time:", total_all_time)
            ]
            
            for i, (label, count) in enumerate(summary_stats):
                period_label = Gtk.Label(label)
                period_label.set_halign(Gtk.Align.END)
                summary_grid.attach(period_label, 0, i, 1, 1)
                
                count_label = Gtk.Label()
                count_label.set_markup(f"<span weight='bold' size='large' color='#FF9800'>{count}</span>")
                count_label.set_halign(Gtk.Align.START)
                summary_grid.attach(count_label, 1, i, 1, 1)
            
            summary_box.pack_start(summary_grid, False, False, 0)
            summary_frame.add(summary_box)
            self.stats_box.pack_start(summary_frame, False, False, 0)
            
            # Add separator
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            separator.set_margin_top(10)
            separator.set_margin_bottom(10)
            self.stats_box.pack_start(separator, False, False, 0)
            
            # Individual file statistics
            files_title = Gtk.Label()
            files_title.set_markup("<span size='large' weight='bold'>Files Statistics</span>")
            files_title.set_halign(Gtk.Align.CENTER)
            files_title.set_margin_bottom(10)
            self.stats_box.pack_start(files_title, False, False, 0)
            
            # Add file statistics widgets
            for filename, stats in sorted_files:
                if stats['total'] > 0:  # Only show files that have been printed
                    file_widget = self.create_file_statistics_widget(filename, stats)
                    self.stats_box.pack_start(file_widget, False, False, 0)
        
        # Add separator before buttons
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(20)
        separator.set_margin_bottom(10)
        self.stats_box.pack_start(separator, False, False, 0)
        
        # Buttons container (horizontal layout for both buttons)
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons_box.set_halign(Gtk.Align.CENTER)
        buttons_box.set_margin_left(10)
        buttons_box.set_margin_right(10)
        buttons_box.set_margin_bottom(20)
        
        # Refresh button
        refresh_button = self._gtk.Button("refresh", "Refresh", "setting_move")
        refresh_button.connect("clicked", self.refresh_data)
        buttons_box.pack_start(refresh_button, True, True, 0)
        
        # Reset button
        reset_button = self._gtk.Button("delete", "Reset Data", "setting_move")
        reset_button.connect("clicked", self.reset_data)
        buttons_box.pack_start(reset_button, True, True, 0)
        
        self.stats_box.pack_start(buttons_box, False, False, 0)
        
        self.stats_box.show_all()

    def refresh_data(self, widget=None):
        """Refresh the statistics display"""
        logging.info("Refreshing print statistics")
        self.load_statistics()

    def reset_data(self, widget=None):
        """Reset all print statistics data"""
        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self._screen,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset Print Statistics"
        )
        dialog.format_secondary_text(
            "Are you sure you want to delete all print history data?\n"
            "This action cannot be undone."
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            try:
                # Clear the history file
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                
                logging.info("Print statistics data has been reset")
                
                # Refresh the display to show empty state
                self.load_statistics()
                
                # Show success message
                success_dialog = Gtk.MessageDialog(
                    transient_for=self._screen,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Data Reset Complete"
                )
                success_dialog.format_secondary_text("All print history data has been successfully cleared.")
                success_dialog.run()
                success_dialog.destroy()
                
            except Exception as e:
                logging.error(f"Error resetting history data: {e}")
                
                # Show error message
                error_dialog = Gtk.MessageDialog(
                    transient_for=self._screen,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Reset Failed"
                )
                error_dialog.format_secondary_text(f"Failed to reset data: {str(e)}")
                error_dialog.run()
                error_dialog.destroy()

    def activate(self):
        """Called when panel becomes active"""
        self.refresh_data()