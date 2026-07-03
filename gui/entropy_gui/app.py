"""Entropy GUI -- a GTK4 + libadwaita front-end for jegly/entropy.

Architecture mirrors jegly/Tesseract: the GUI never re-implements the core
logic, it just builds an argv for the vendored entropy.py, launches it as a
subprocess, and renders its output. See runner.py for the process plumbing
and theme.py for the palette/CSS engine lifted from Tesseract.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import config, theme  # noqa: E402
from .runner import EXIT_MESSAGES, GenerationJob, format_size_arg  # noqa: E402

APP_ID = "com.jegly.entropygui"
APP_VERSION = "1.0.0"

UNITS = ["KB", "MB", "GB", "TB"]
FORMATS = ["Binary", "Text", "Image (PNG)", "Audio (WAV)"]
SOURCES = ["Cryptographically secure", "Fast (non-crypto)", "Mixed (multiple sources)"]

_SHANNON_RE = re.compile(r"Shannon entropy:\s*([\d.]+)\s*bits/byte")
_VIZ_RE = re.compile(r"Visualization:\s*(.+\.png)")

# Measured throughput (MB/s) on the reference dev machine. entropy.py's
# Binary/Image/Audio generators always pull random bytes in large (up to 1MB)
# chunks, so they're fast regardless of source. The Text generator instead
# pulls one character (or, in Markov mode, one word) at a time -- so it's
# 60-2000x slower, and *worse* with Markov on (a separate file.write() per
# word beats the per-character rejection-sampling loop). Mixed source makes
# every one of those per-character/word pulls redo the whole multi-source
# collection instead of amortizing it over a bulk chunk.
_BULK_MBPS = 100.0
_TEXT_MBPS = {
    ("crypto", False): 1.5, ("crypto", True): 0.7,
    ("fast", False): 1.5, ("fast", True): 0.7,
    ("mixed", False): 0.05, ("mixed", True): 0.05,
}
_SLOW_CONFIRM_SECONDS = 8.0


def human_bytes(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n:.2f}PB"


class EntropyWindow(Adw.ApplicationWindow):
    def __init__(self, app: "EntropyApp"):
        super().__init__(application=app)
        self.app = app
        self.settings = app.settings
        self.job: GenerationJob | None = None
        self.output_dir = self.settings.defaults.output_dir or str(Path.home())

        self.set_title("Entropy")
        self.set_default_size(
            self.settings.appearance.window_width, self.settings.appearance.window_height
        )

        self.toasts = Adw.ToastOverlay()
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._build_body())
        self.toasts.set_child(toolbar)
        self.set_content(self.toasts)

        self.connect("close-request", self._on_close_request)
        self._poll_entropy_pool()
        GLib.timeout_add_seconds(5, self._poll_entropy_pool)

    # ---------------------------------------------------------------- header
    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new("Entropy", ""))

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu()
        main_section = Gio.Menu()
        main_section.append("How to use…", "app.guide")
        main_section.append("Preferences…", "app.preferences")
        menu.append_section(None, main_section)
        about_section = Gio.Menu()
        about_section.append("About Entropy", "app.about")
        menu.append_section(None, about_section)
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        return header

    # ------------------------------------------------------------------ body
    def _build_body(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow(vexpand=True)
        clamp = Adw.Clamp(maximum_size=760, margin_top=18, margin_bottom=18,
                           margin_start=16, margin_end=16)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        clamp.set_child(outer)
        scroll.set_child(clamp)

        outer.append(self._build_size_format_card())
        outer.append(self._build_source_card())
        outer.append(self._build_output_card())
        outer.append(self._build_extras_card())

        self.generate_btn = Gtk.Button(label="Generate")
        self.generate_btn.add_css_class("suggested-action")
        self.generate_btn.add_css_class("pill")
        self.generate_btn.set_size_request(-1, 42)
        self.generate_btn.connect("clicked", self._on_generate_clicked)
        outer.append(self.generate_btn)

        outer.append(self._build_progress_section())
        outer.append(self._build_results_section())

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        body.append(scroll)
        body.append(self._build_footer())
        return body

    def _card(self, title: str, subtitle: str = "") -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=title)
        if subtitle:
            group.set_description(subtitle)
        return group

    def _build_size_format_card(self) -> Gtk.Widget:
        group = self._card("Size and Format")

        size_row = Adw.ActionRow(title="Size")
        suffix = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.size_spin = Gtk.SpinButton()
        self.size_spin.set_adjustment(Gtk.Adjustment(value=10, lower=0.01, upper=999999, step_increment=1, page_increment=10))
        self.size_spin.set_digits(2)
        self.size_spin.set_numeric(True)
        self.size_spin.set_valign(Gtk.Align.CENTER)
        self.unit_dropdown = Gtk.DropDown.new_from_strings(UNITS)
        self.unit_dropdown.set_selected(1)  # MB
        self.unit_dropdown.set_valign(Gtk.Align.CENTER)
        suffix.append(self.size_spin)
        suffix.append(self.unit_dropdown)
        size_row.add_suffix(suffix)
        group.add(size_row)

        self.format_combo = Adw.ComboRow(title="Format")
        self.format_combo.set_model(Gtk.StringList.new(FORMATS))
        default_idx = {"bin": 0, "txt": 1, "img": 2, "audio": 3}.get(self.settings.defaults.format, 0)
        self.format_combo.set_selected(default_idx)
        self.format_combo.connect("notify::selected", self._on_format_changed)
        group.add(self.format_combo)

        self.markov_row = Adw.SwitchRow(
            title="Markov-style word sequences",
            subtitle="Real English/lorem words instead of random printable characters",
        )
        self.markov_row.connect("notify::active", lambda *_: self._sync_text_rows())
        group.add(self.markov_row)

        self.lorem_row = Adw.SwitchRow(
            title="Lorem ipsum style",
            subtitle="Classic filler-text words (needs Markov mode above)",
        )
        group.add(self.lorem_row)

        self._sync_text_rows()
        return group

    def _on_format_changed(self, *_a) -> None:
        self._sync_text_rows()

    def _sync_text_rows(self) -> None:
        is_text = self.format_combo.get_selected() == 1
        self.markov_row.set_sensitive(is_text)
        self.lorem_row.set_sensitive(is_text and self.markov_row.get_active())

    def _build_source_card(self) -> Gtk.Widget:
        group = self._card("Entropy Source")

        self.source_combo = Adw.ComboRow(title="Source")
        self.source_combo.set_model(Gtk.StringList.new(SOURCES))
        default_idx = {"crypto": 0, "fast": 1, "mixed": 2}.get(self.settings.defaults.source, 0)
        self.source_combo.set_selected(default_idx)
        self.source_combo.connect("notify::selected", lambda *_: self._sync_source_rows())
        group.add(self.source_combo)

        self.seed_row = Adw.SpinRow.new_with_range(0, 2**31 - 1, 1)
        self.seed_row.set_title("Seed")
        self.seed_row.set_subtitle("Reproducible output -- only takes effect in Fast mode")
        group.add(self.seed_row)

        self.use_env_row = Adw.SwitchRow(
            title="Mix in system environment data",
            subtitle="Load average, memory, network stats, thermal sensors",
        )
        group.add(self.use_env_row)

        self.microphone_row = Adw.SwitchRow(
            title="Mix in microphone noise", subtitle="Requires arecord (alsa-utils)"
        )
        group.add(self.microphone_row)

        self.camera_row = Adw.SwitchRow(
            title="Mix in camera static", subtitle="Requires v4l2-ctl (v4l-utils)"
        )
        group.add(self.camera_row)

        self.speed_notice = Gtk.Revealer()
        notice_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        notice_box.add_css_class("ent-help")
        notice_box.set_margin_top(4)
        self.speed_notice_label = Gtk.Label(wrap=True, xalign=0.0)
        notice_box.append(self.speed_notice_label)
        self.speed_notice.set_child(notice_box)
        group.add(self.speed_notice)

        for widget, signal in (
            (self.format_combo, "notify::selected"),
            (self.source_combo, "notify::selected"),
            (self.markov_row, "notify::active"),
            (self.use_env_row, "notify::active"),
            (self.microphone_row, "notify::active"),
            (self.camera_row, "notify::active"),
            (self.size_spin, "value-changed"),
            (self.unit_dropdown, "notify::selected"),
        ):
            widget.connect(signal, lambda *_: self._sync_speed_notice())
        self._sync_source_rows()
        self._sync_speed_notice()
        return group

    def _sync_source_rows(self) -> None:
        sel = self.source_combo.get_selected()
        self.seed_row.set_sensitive(sel == 1)
        for row in (self.use_env_row, self.microphone_row, self.camera_row):
            row.set_sensitive(sel == 2)

    def _source_key(self) -> str:
        return ["crypto", "fast", "mixed"][self.source_combo.get_selected()]

    def _has_extra_subsource(self) -> bool:
        return (
            self.use_env_row.get_active()
            or self.microphone_row.get_active()
            or self.camera_row.get_active()
        )

    def _estimate_seconds(self, total_bytes: int) -> float:
        """Rough projection from measured throughput; None means "fast, no
        need to warn" (binary/image/audio -- always bulk regardless of source)."""
        if self.format_combo.get_selected() != 1:
            return 0.0
        source = self._source_key()
        if source == "mixed" and self._has_extra_subsource():
            return float("inf")
        mbps = _TEXT_MBPS[(source, self.markov_row.get_active())]
        return (total_bytes / (1024 * 1024)) / mbps

    def _sync_speed_notice(self) -> None:
        value = self.size_spin.get_value()
        unit = UNITS[self.unit_dropdown.get_selected()]
        multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        total_bytes = int(value * multipliers[unit])
        seconds = self._estimate_seconds(total_bytes)
        if seconds < 2.0:
            self.speed_notice.set_reveal_child(False)
            return
        self.speed_notice_label.set_text(self._speed_message(seconds))
        self.speed_notice.set_reveal_child(True)

    def _speed_message(self, seconds: float) -> str:
        source = self._source_key()
        if seconds == float("inf"):
            return (
                "Text output is generated one character at a time, and Mixed "
                "source re-triggers the whole multi-source collection for "
                "every one of them -- with environment/microphone/camera "
                "mixing on, that can hang for a very long time. Turn those "
                "off, use Binary/Image/Audio with Mixed instead, or switch to "
                "Crypto/Fast for Text."
            )
        if source == "mixed":
            return (
                f"Text + Mixed source measured about 60x slower than Crypto here "
                f"(~{seconds:.0f}s projected). Prefer Crypto/Fast for Text, or "
                "Binary/Image/Audio if you want Mixed source."
            )
        return (
            f"Text is generated one character (or word) at a time, not in bulk "
            f"-- about {seconds:.0f}s projected for this size. Binary/Image/"
            "Audio are near-instant at any size if you don't need text output."
        )

    def _build_output_card(self) -> Gtk.Widget:
        group = self._card("Output")

        self.folder_row = Adw.ActionRow(title="Destination folder", subtitle=self.output_dir)
        choose_btn = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose_btn.connect("clicked", self._on_choose_folder)
        self.folder_row.add_suffix(choose_btn)
        group.add(self.folder_row)

        self.multi_row = Adw.SpinRow.new_with_range(1, 999, 1)
        self.multi_row.set_title("Split into files")
        self.multi_row.set_subtitle("Divide the total size evenly across N files")
        group.add(self.multi_row)

        return group

    def _build_extras_card(self) -> Gtk.Widget:
        group = self._card("Analysis and Extras")

        self.analyze_row = Adw.SwitchRow(
            title="Shannon entropy analysis", subtitle="Bits/byte -- 8.0 is perfectly random"
        )
        group.add(self.analyze_row)

        self.visualize_row = Adw.SwitchRow(
            title="Byte-frequency heatmap", subtitle="Saves a PNG visualization alongside the file"
        )
        group.add(self.visualize_row)

        self.hexdump_row = Adw.SwitchRow(title="Hexdump preview", subtitle="First/last 256 bytes")
        group.add(self.hexdump_row)

        self.benchmark_row = Adw.SwitchRow(
            title="Benchmark source first", subtitle="~100MB throughput test before generating"
        )
        group.add(self.benchmark_row)

        self.monitor_row = Adw.SwitchRow(
            title="Show system entropy pool", subtitle="/proc/sys/kernel/random/entropy_avail"
        )
        group.add(self.monitor_row)

        return group

    def _build_progress_section(self) -> Gtk.Widget:
        self.progress_revealer = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("ent-card")
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(10)
        box.set_margin_end(10)

        self.progress_bar = Gtk.ProgressBar(show_text=True)
        box.append(self.progress_bar)

        self.progress_detail = Gtk.Label(label="", xalign=0.0)
        self.progress_detail.add_css_class("ent-dim")
        box.append(self.progress_detail)

        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.add_css_class("destructive-action")
        self.cancel_btn.set_halign(Gtk.Align.START)
        self.cancel_btn.connect("clicked", self._on_cancel_clicked)
        box.append(self.cancel_btn)

        self.progress_revealer.set_child(box)
        self.progress_revealer.set_reveal_child(False)
        return self.progress_revealer

    def _build_results_section(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.analysis_revealer = Gtk.Revealer()
        analysis_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        analysis_box.add_css_class("ent-card")
        analysis_box.set_margin_top(6)
        analysis_box.set_margin_bottom(6)
        analysis_box.set_margin_start(10)
        analysis_box.set_margin_end(10)
        analysis_box.append(Gtk.Label(label="Shannon entropy", xalign=0.0, css_classes=["ent-section-title"]))
        self.entropy_level = Gtk.LevelBar(min_value=0, max_value=8, value=0)
        self.entropy_level.add_offset_value("low", 6.0)
        self.entropy_level.add_offset_value("high", 7.5)
        analysis_box.append(self.entropy_level)
        self.entropy_label = Gtk.Label(label="", xalign=0.0, css_classes=["ent-dim"])
        analysis_box.append(self.entropy_label)
        self.analysis_revealer.set_child(analysis_box)
        self.analysis_revealer.set_reveal_child(False)
        container.append(self.analysis_revealer)

        self.viz_revealer = Gtk.Revealer()
        viz_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        viz_box.add_css_class("ent-card")
        viz_box.set_margin_top(6)
        viz_box.set_margin_bottom(6)
        viz_box.set_margin_start(10)
        viz_box.set_margin_end(10)
        viz_box.append(Gtk.Label(label="Byte-frequency heatmap", xalign=0.0, css_classes=["ent-section-title"]))
        self.viz_picture = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN)
        self.viz_picture.set_size_request(-1, 110)
        viz_box.append(self.viz_picture)
        self.viz_revealer.set_child(viz_box)
        self.viz_revealer.set_reveal_child(False)
        container.append(self.viz_revealer)

        expander = Gtk.Expander(label="Output log")
        log_scroll = Gtk.ScrolledWindow(min_content_height=180, vexpand=False)
        self.log_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        self.log_view.add_css_class("ent-mono")
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_top_margin(8)
        self.log_view.set_bottom_margin(8)
        self.log_view.set_left_margin(8)
        self.log_view.set_right_margin(8)
        log_scroll.set_child(self.log_view)
        expander.set_child(log_scroll)
        container.append(expander)

        return container

    def _build_footer(self) -> Gtk.Widget:
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer.add_css_class("ent-statusbar")
        self.pool_dot = Gtk.Label(label="●")
        self.pool_dot.add_css_class("ent-dim")
        self.pool_label = Gtk.Label(label="Entropy pool: --", xalign=0.0, hexpand=True)
        self.pool_label.add_css_class("ent-dim")
        footer.append(self.pool_dot)
        footer.append(self.pool_label)
        footer.set_visible(self.settings.appearance.show_status_bar)
        self.footer = footer
        return footer

    # ------------------------------------------------------------- behaviour
    def _on_choose_folder(self, _btn) -> None:
        dialog = Gtk.FileDialog(title="Choose destination folder")
        try:
            dialog.set_initial_folder(Gio.File.new_for_path(self.output_dir))
        except GLib.Error:
            pass

        def on_response(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
            except GLib.Error:
                return
            if folder:
                self.output_dir = folder.get_path()
                self.folder_row.set_subtitle(self.output_dir)

        dialog.select_folder(self, None, on_response)

    def _build_args(self) -> tuple[list[str], int]:
        value = self.size_spin.get_value()
        unit = UNITS[self.unit_dropdown.get_selected()]
        args = [format_size_arg(value, unit)]

        multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        total_bytes = int(value * multipliers[unit])

        fmt_idx = self.format_combo.get_selected()
        args.append(["-bin", "-txt", "-img", "-audio"][fmt_idx])
        if fmt_idx == 1:
            if self.markov_row.get_active():
                args.append("--markov")
                if self.lorem_row.get_active():
                    args.append("--lorem")

        src_idx = self.source_combo.get_selected()
        if src_idx == 1:
            args.append("--fast")
            args += ["--seed", str(int(self.seed_row.get_value()))]
        elif src_idx == 2:
            args.append("--mixed")
            if self.use_env_row.get_active():
                args.append("--use-env")
            if self.microphone_row.get_active():
                args.append("--microphone")
            if self.camera_row.get_active():
                args.append("--camera")

        multi = int(self.multi_row.get_value())
        if multi > 1:
            args += ["-multi", str(multi)]

        if self.analyze_row.get_active():
            args.append("--analyze")
        if self.visualize_row.get_active():
            args.append("--visualize")
        if self.hexdump_row.get_active():
            args.append("--hexdump")
        if self.benchmark_row.get_active():
            args.append("--benchmark")
        if self.monitor_row.get_active():
            args.append("--monitor-entropy")

        # The GUI owns file naming/collisions (timestamped filenames, chosen
        # folder); force keeps entropy.py from blocking on a stdin prompt
        # this headless subprocess can't answer.
        args.append("-force")
        return args, total_bytes

    def _on_generate_clicked(self, _btn) -> None:
        if self.job is not None:
            return
        args, total_bytes = self._build_args()

        seconds = self._estimate_seconds(total_bytes)
        if seconds > _SLOW_CONFIRM_SECONDS:
            self._confirm_slow_run(args, total_bytes, seconds)
            return

        self._check_space_then_start(args, total_bytes)

    def _check_space_then_start(self, args: list[str], total_bytes: int) -> None:
        try:
            free = shutil.disk_usage(self.output_dir).free
        except OSError:
            free = None
        if free is not None and total_bytes > free:
            self._confirm_low_space(args, total_bytes, free)
            return
        self._start_job(args)

    def _confirm_slow_run(self, args: list[str], total_bytes: int, seconds: float) -> None:
        heading = "This could take a very long time" if seconds == float("inf") else "This is going to be slow"
        dialog = Adw.MessageDialog(
            heading=heading,
            body=self._speed_message(seconds),
            transient_for=self,
            modal=True,
        )
        dialog.add_response("cancel", "Cancel")
        offer_crypto = self._source_key() != "crypto"
        if offer_crypto:
            dialog.add_response("crypto", "Use Crypto source instead")
        dialog.add_response("go", "Continue anyway")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("crypto" if offer_crypto else "cancel")

        def on_response(_d, resp):
            if resp == "crypto":
                self.source_combo.set_selected(0)
                new_args, new_total = self._build_args()
                self._check_space_then_start(new_args, new_total)
            elif resp == "go":
                self._check_space_then_start(args, total_bytes)

        dialog.connect("response", on_response)
        dialog.present()

    def _confirm_low_space(self, args: list[str], total_bytes: int, free: int) -> None:
        dialog = Adw.MessageDialog(
            heading="Not enough free space?",
            body=(
                f"You're asking for {human_bytes(total_bytes)} but "
                f"{self.output_dir} only reports {human_bytes(free)} free.\n\n"
                "entropy.py will stop safely before writing if this is right, "
                "but you can cancel now instead."
            ),
            transient_for=self,
            modal=True,
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("go", "Try anyway")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(_d, resp):
            if resp == "go":
                self._start_job(args)

        dialog.connect("response", on_response)
        dialog.present()

    def _start_job(self, args: list[str]) -> None:
        self.log_buffer_clear()
        self.analysis_revealer.set_reveal_child(False)
        self.viz_revealer.set_reveal_child(False)
        self.generate_btn.set_sensitive(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Starting…")
        self.progress_detail.set_text("")
        self.progress_revealer.set_reveal_child(True)

        self.job = GenerationJob(
            args=args,
            cwd=self.output_dir,
            on_progress=self._on_progress,
            on_line=self._on_line,
            on_done=self._on_done,
        )
        self.append_log(f"$ {self.job.command_preview()}\n")
        self.job.start()

    def _on_cancel_clicked(self, _btn) -> None:
        if self.job:
            self.job.cancel()
            self.cancel_btn.set_sensitive(False)

    def _on_progress(self, percent: float, written: str, speed: str, eta: int) -> bool:
        self.progress_bar.set_fraction(min(percent / 100.0, 1.0))
        self.progress_bar.set_text(f"{percent:.1f}%")
        self.progress_detail.set_text(f"{written} written · {speed}/s · ETA {eta}s")
        return False

    def _on_line(self, line: str) -> bool:
        self.append_log(line + "\n")
        m = _SHANNON_RE.search(line)
        if m:
            value = float(m.group(1))
            self.entropy_level.set_value(value)
            self.entropy_label.set_text(f"{value:.4f} bits/byte")
            self.analysis_revealer.set_reveal_child(True)
        m = _VIZ_RE.search(line)
        if m and os.path.exists(m.group(1)):
            self.viz_picture.set_filename(m.group(1))
            self.viz_revealer.set_reveal_child(True)
        return False

    def _on_done(self, code: int, cancelled: bool) -> bool:
        self.job = None
        self.generate_btn.set_sensitive(True)
        self.cancel_btn.set_sensitive(True)
        self.progress_revealer.set_reveal_child(False)

        if cancelled:
            self.toasts.add_toast(Adw.Toast(
                title=f"Cancelled -- a partial file may remain in {self.output_dir}", timeout=6
            ))
        elif code == 0:
            self.toasts.add_toast(Adw.Toast.new("Generation complete"))
        else:
            msg = EXIT_MESSAGES.get(code, f"Exited with code {code}")
            self.toasts.add_toast(Adw.Toast(title=f"Error: {msg}", timeout=6))
        return False

    def log_buffer_clear(self) -> None:
        buf = self.log_view.get_buffer()
        buf.set_text("")

    def append_log(self, text: str) -> None:
        buf = self.log_view.get_buffer()
        buf.insert(buf.get_end_iter(), text)
        buf.place_cursor(buf.get_end_iter())
        self.log_view.scroll_mark_onscreen(buf.get_insert())

    def _poll_entropy_pool(self) -> bool:
        try:
            with open("/proc/sys/kernel/random/entropy_avail") as f:
                avail = int(f.read().strip())
            self.pool_dot.remove_css_class("error")
            self.pool_dot.add_css_class("ent-dim" if avail >= 1000 else "warning")
            self.pool_label.set_text(f"Entropy pool: {avail} bits")
        except OSError:
            self.pool_label.set_text("Entropy pool: unavailable")
        return True

    def _on_close_request(self, *_a) -> bool:
        s = self.settings
        if s.appearance.remember_window:
            s.appearance.window_width = self.get_width()
            s.appearance.window_height = self.get_height()
        s.defaults.output_dir = self.output_dir
        s.defaults.format = ["bin", "txt", "img", "audio"][self.format_combo.get_selected()]
        s.defaults.source = ["crypto", "fast", "mixed"][self.source_combo.get_selected()]
        s.save()
        if self.job:
            self.job.cancel()
        return False


class EntropyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.settings = config.Settings.load()
        self.css = Gtk.CssProvider()
        self.win: EntropyWindow | None = None

    def do_activate(self) -> None:
        if self.win is None:
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display, self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER
                )
                icon_theme = Gtk.IconTheme.get_for_display(display)
                icon_dir = Path(__file__).resolve().parent.parent / "packaging" / "icons"
                if icon_dir.exists():
                    icon_theme.add_search_path(str(icon_dir))
            Gtk.Window.set_default_icon_name(APP_ID)
            self.apply_theme()
            self.win = EntropyWindow(self)
            self._register_actions()
        self.win.present()

    def apply_theme(self) -> None:
        palette = theme.find_theme(self.settings.appearance.theme)
        style = Adw.StyleManager.get_default()
        if palette.follow_system:
            style.set_color_scheme(Adw.ColorScheme.DEFAULT)
        elif palette.dark:
            style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        css_text = theme.compile_css(
            palette,
            self.settings.appearance.accent,
            self.settings.appearance.glow_intensity,
            self.settings.appearance.density,
            "",
        )
        self.css.load_from_string(css_text)

    def _register_actions(self) -> None:
        def add_action(name, cb):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", cb)
            self.add_action(action)

        add_action("preferences", lambda *_: self._open_preferences())
        add_action("about", lambda *_: self._show_about())
        add_action("guide", lambda *_: self._show_guide())
        self.set_accels_for_action("app.preferences", ["<Ctrl>comma"])

    def _open_preferences(self) -> None:
        from .preferences import PreferencesWindow

        win = PreferencesWindow(self)
        win.present()

    def _show_about(self) -> None:
        about = Adw.AboutWindow(
            application_name="Entropy",
            application_icon=APP_ID,
            version=APP_VERSION,
            developer_name="jegly",
            license_type=Gtk.License.MIT_X11,
            comments=(
                "A GTK4 + libadwaita front-end for the entropy.py random data "
                "generator. The GUI never re-implements the generator -- it "
                "drives the upstream CLI as a subprocess and renders its output."
            ),
            website="https://github.com/jegly/entropy",
        )
        about.set_transient_for(self.win)
        about.present()

    def _show_guide(self) -> None:
        win = Adw.PreferencesWindow(
            title="How to use Entropy", modal=True, transient_for=self.win,
            default_width=640, default_height=560, search_enabled=False,
        )
        page = Adw.PreferencesPage(title="Guide", icon_name="dialog-information-symbolic")
        rows = [
            ("Pick a size and format",
             "Choose how much data you need and what shape it should take: raw "
             "binary, printable text, a PNG image, or a WAV audio file."),
            ("Choose an entropy source",
             "Cryptographically secure (/dev/urandom) is right for almost "
             "everything. Fast trades security for speed using a plain PRNG -- "
             "only use it for non-sensitive test data. Mixed blends in extra "
             "sources (system noise, hardware RNG, microphone, camera) for "
             "higher-quality randomness at the cost of speed."),
            ("Seed only works in Fast mode",
             "entropy.py's --seed reseeds Python's plain random module, which "
             "only the Fast generator consumes. Crypto and Mixed modes always "
             "read from the OS, so a seed can't make them reproducible."),
            ("Lorem ipsum needs Markov mode",
             "The text generator only picks whole words (English or lorem "
             "ipsum) when Markov-style sequencing is on; otherwise it emits "
             "random printable characters and the word-list choice is unused."),
            ("Analysis and Extras",
             "Shannon entropy analysis, the byte-frequency heatmap, and the "
             "hexdump preview all run against the file(s) you just generated "
             "and show up below the Generate button when they finish."),
            ("Where files go",
             "Files land in the destination folder you pick, named "
             "entropy_TIMESTAMP.EXT -- exactly like running entropy.py "
             "from a terminal in that folder."),
        ]
        group = Adw.PreferencesGroup()
        for title, body in rows:
            row = Adw.ActionRow(title=title, subtitle=body)
            row.set_subtitle_lines(0)
            row.set_title_lines(0)
            group.add(row)
        page.add(group)
        win.add(page)
        win.present()
