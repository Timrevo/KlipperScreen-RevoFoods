import os
import json
from datetime import datetime, timedelta

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel

class Panel(ScreenPanel):
    def __init__(self, screen, title):
        title = title or _("Print Times")
        super().__init__(screen, title)
        self.print_times_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'print_times.json')
        self.history_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'history.json')
        self.week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.current_week_offset = 0  # 0 = this week, -1 = previous, +1 = next
        self.build_panel()

    def build_panel(self):
        self.content.foreach(lambda widget: self.content.remove(widget))
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_homogeneous(False)

        # Title
        title_label = Gtk.Label()
        week_start, week_end = self.get_week_range(self.current_week_offset)
        title_label.set_markup(
            f"<span size='large' weight='bold'>Production Times<br>{week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}</span>"
        )
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.pack_start(title_label, False, False, 10)

        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        prev_btn = Gtk.Button(label="◀")
        prev_btn.set_size_request(40, 40)
        prev_btn.connect("clicked", self.change_week, -1)
        nav_box.pack_start(prev_btn, False, False, 0)

        # Week number label
        week_number = week_start.isocalendar()[1]
        week_label = Gtk.Label(label=f"Week {week_number}")
        week_label.set_halign(Gtk.Align.CENTER)
        nav_box.pack_start(week_label, True, True, 0)

        next_btn = Gtk.Button(label="▶")
        next_btn.set_size_request(40, 40)
        next_btn.connect("clicked", self.change_week, 1)
        nav_box.pack_start(next_btn, False, False, 0)

        main_box.pack_start(nav_box, False, False, 0)

        # Week days buttons
        week_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        times_data = self.load_times_data()
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            btn = Gtk.Button(label=self.week_days[i])
            btn.set_size_request(60, 60)
            btn.connect("clicked", self.show_day_details, day_str)
            if day_str in times_data:
                btn.set_tooltip_text(f"{times_data[day_str]['first']} - {times_data[day_str]['last']}")
            else:
                btn.set_tooltip_text("/")
            week_box.pack_start(btn, True, True, 0)
        main_box.pack_start(week_box, False, False, 10)

        # Details area (VBox for ergonomic display)
        self.details_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.details_area.set_homogeneous(False)
        # Affiche le jour actuel par défaut
        today = datetime.now().date()
        if today >= week_start and today <= week_end:
            self.show_day_details(None, today.strftime("%Y-%m-%d"))
        else:
            self.show_day_details(None, week_start.strftime("%Y-%m-%d"))
        main_box.pack_start(self.details_area, False, False, 10)

        # Separator before buttons
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(20)
        separator.set_margin_bottom(10)
        main_box.pack_start(separator, False, False, 0)

        # Buttons container (horizontal layout for both buttons)
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons_box.set_halign(Gtk.Align.CENTER)
        buttons_box.set_margin_left(10)
        buttons_box.set_margin_right(10)
        buttons_box.set_margin_bottom(20)

        # Refresh button
        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.set_size_request(100, 40)
        refresh_button.connect("clicked", self.refresh_data)
        buttons_box.pack_start(refresh_button, True, True, 0)

        # Reset button
        reset_button = Gtk.Button(label="Reset Data")
        reset_button.set_size_request(100, 40)
        reset_button.connect("clicked", self.reset_data)
        buttons_box.pack_start(reset_button, True, True, 0)

        main_box.pack_start(buttons_box, False, False, 0)

        self.content.add(main_box)
        self.content.show_all()
    def load_history_data(self):
        try:
            if os.path.exists(self.history_file) and os.path.getsize(self.history_file) > 0:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get_week_range(self, offset=0):
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
        sunday = monday + timedelta(days=6)
        return monday, sunday

    def change_week(self, widget, offset):
        self.current_week_offset += offset
        self.build_panel()

    def load_times_data(self):
        try:
            if os.path.exists(self.print_times_file) and os.path.getsize(self.print_times_file) > 0:
                with open(self.print_times_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def show_day_details(self, widget, day_str):
        # Clear previous details
        self.details_area.foreach(lambda w: self.details_area.remove(w))
        times_data = self.load_times_data()
        history_data = self.load_history_data()

        # Date title
        date_label = Gtk.Label()
        date_label.set_markup(f"<span size='x-large' weight='bold'>{day_str}</span>")
        date_label.set_halign(Gtk.Align.CENTER)
        self.details_area.pack_start(date_label, False, False, 6)

        # Production times info
        times_frame = Gtk.Frame()
        times_frame.set_shadow_type(Gtk.ShadowType.IN)
        times_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        times_box.set_homogeneous(False)
        if day_str in times_data:
            first = times_data[day_str]['first']
            last = times_data[day_str]['last']
            first_label = Gtk.Label()
            first_label.set_markup(f"<span size='medium'>First cycle: <b>{first}</b></span>")
            first_label.set_halign(Gtk.Align.CENTER)
            last_label = Gtk.Label()
            last_label.set_markup(f"<span size='medium'>Last cycle: <b>{last}</b></span>")
            last_label.set_halign(Gtk.Align.CENTER)
            times_box.pack_start(first_label, True, True, 10)
            times_box.pack_start(last_label, True, True, 10)
        else:
            no_label = Gtk.Label()
            no_label.set_markup("<span size='medium'>No production recorded for this day.</span>")
            no_label.set_halign(Gtk.Align.CENTER)
            times_box.pack_start(no_label, True, True, 10)
        times_frame.add(times_box)
        self.details_area.pack_start(times_frame, False, False, 6)

        # Print jobs info
        jobs_title = Gtk.Label()
        jobs_title.set_markup("<span size='large' weight='bold'>Production Jobs</span>")
        jobs_title.set_halign(Gtk.Align.CENTER)
        self.details_area.pack_start(jobs_title, False, False, 4)

        jobs_flow_align = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        jobs_flow_align.set_homogeneous(True)
        jobs_flow_align.set_halign(Gtk.Align.CENTER)

        jobs_flow = Gtk.FlowBox()
        jobs_flow.set_max_children_per_line(3)
        jobs_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        jobs_flow.set_halign(Gtk.Align.CENTER)

        found_job = False
        for filename, days in history_data.items():
            if day_str in days:
                found_job = True
                icon_name = self.get_file_icon(filename)
                job_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                job_box.set_homogeneous(False)
                icon_img = self._gtk.Image(icon_name, 200, 200)
                icon_img.set_halign(Gtk.Align.CENTER)
                job_box.pack_start(icon_img, False, False, 0)
                file_label = Gtk.Label()
                file_label.set_markup(f"<span size='large'><b>{filename}</b></span>")
                file_label.set_halign(Gtk.Align.CENTER)
                job_box.pack_start(file_label, False, False, 0)
                count_label = Gtk.Label()
                count_label.set_markup(f"<span size='medium'>{days[day_str]} cycle(s)</span>")
                count_label.set_halign(Gtk.Align.CENTER)
                job_box.pack_start(count_label, False, False, 0)
                frame = Gtk.Frame()
                frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
                frame.add(job_box)
                jobs_flow.add(frame)
        if not found_job:
            job_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            job_box.set_homogeneous(False)
            file_label = Gtk.Label()
            file_label.set_markup("<span size='large'>No production jobs for this day.</span>")
            file_label.set_halign(Gtk.Align.CENTER)
            job_box.pack_start(file_label, True, True, 0)
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
            frame.add(job_box)
            jobs_flow.add(frame)

        jobs_flow_align.pack_start(jobs_flow, True, True, 0)
        self.details_area.pack_start(jobs_flow_align, False, False, 6)
        self.details_area.show_all()
    def refresh_data(self, widget=None):
        """Refresh the panel display"""
        self.build_panel()

    def reset_data(self, widget=None):
        """Reset all print times data"""
        dialog = Gtk.MessageDialog(
            transient_for=self._screen,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset Print Times Data"
        )
        dialog.format_secondary_text(
            "Are you sure you want to delete all print times data?\nThis action cannot be undone."
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            try:
                with open(self.print_times_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                self.refresh_data()
                success_dialog = Gtk.MessageDialog(
                    transient_for=self._screen,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Data Reset Complete"
                )
                success_dialog.format_secondary_text("All print times data has been successfully cleared.")
                success_dialog.run()
                success_dialog.destroy()
            except Exception as e:
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