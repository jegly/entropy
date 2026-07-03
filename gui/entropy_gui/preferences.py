"""Appearance preferences -- theme picker, accent override, density.
Mirrors jegly/Tesseract's settings_ui: every change applies live."""

from __future__ import annotations

from gi.repository import Adw, Gdk, Gtk

from . import theme


class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, app):
        super().__init__(title="Preferences", modal=True, transient_for=app.win,
                          default_width=520, default_height=560, search_enabled=False)
        self.app = app
        self.settings = app.settings

        page = Adw.PreferencesPage(title="Appearance", icon_name="applications-graphics-symbolic")
        page.add(self._build_theme_group())
        page.add(self._build_behavior_group())
        self.add(page)

    def _build_theme_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Theme", description="Same palette engine as Tesseract")
        palettes = theme.builtin_themes()
        names = [p.name for p in palettes]

        self.theme_combo = Adw.ComboRow(title="Palette")
        self.theme_combo.set_model(Gtk.StringList.new(names))
        current_idx = next((i for i, p in enumerate(palettes) if p.id == self.settings.appearance.theme), 0)
        self.theme_combo.set_selected(current_idx)
        self.theme_combo.connect("notify::selected", self._on_theme_changed)
        group.add(self.theme_combo)

        accent_row = Adw.ActionRow(title="Accent override", subtitle="Leave unset to use the palette's own accent")
        self.accent_btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(), valign=Gtk.Align.CENTER)
        rgba = Gdk.RGBA()
        if self.settings.appearance.accent and rgba.parse(self.settings.appearance.accent):
            self.accent_btn.set_rgba(rgba)
        self.accent_btn.connect("notify::rgba", self._on_accent_changed)
        accent_row.add_suffix(self.accent_btn)
        clear_btn = Gtk.Button(icon_name="edit-clear-symbolic", valign=Gtk.Align.CENTER)
        clear_btn.set_tooltip_text("Clear override")
        clear_btn.connect("clicked", self._on_accent_clear)
        accent_row.add_suffix(clear_btn)
        group.add(accent_row)

        self.glow_row = Adw.SpinRow.new_with_range(0, 100, 5)
        self.glow_row.set_title("Neon glow intensity")
        self.glow_row.set_subtitle("Only visible on glow-capable themes (e.g. Neon Tessera)")
        self.glow_row.set_value(self.settings.appearance.glow_intensity)
        self.glow_row.connect("notify::value", self._on_glow_changed)
        group.add(self.glow_row)

        return group

    def _build_behavior_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Behavior")

        self.density_row = Adw.SwitchRow(title="Compact density", subtitle="Tighter row spacing")
        self.density_row.set_active(self.settings.appearance.density == "compact")
        self.density_row.connect("notify::active", self._on_density_changed)
        group.add(self.density_row)

        self.remember_row = Adw.SwitchRow(title="Remember window size")
        self.remember_row.set_active(self.settings.appearance.remember_window)
        self.remember_row.connect("notify::active", self._on_remember_changed)
        group.add(self.remember_row)

        self.statusbar_row = Adw.SwitchRow(title="Show status bar", subtitle="Entropy pool footer")
        self.statusbar_row.set_active(self.settings.appearance.show_status_bar)
        self.statusbar_row.connect("notify::active", self._on_statusbar_changed)
        group.add(self.statusbar_row)

        return group

    def _on_theme_changed(self, *_a) -> None:
        idx = self.theme_combo.get_selected()
        palette = theme.builtin_themes()[idx]
        self.settings.appearance.theme = palette.id
        self._apply()

    def _on_accent_changed(self, *_a) -> None:
        rgba = self.accent_btn.get_rgba()
        self.settings.appearance.accent = "#%02x%02x%02x" % (
            round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255)
        )
        self._apply()

    def _on_accent_clear(self, *_a) -> None:
        self.settings.appearance.accent = ""
        self.accent_btn.set_rgba(Gdk.RGBA())
        self._apply()

    def _on_glow_changed(self, *_a) -> None:
        self.settings.appearance.glow_intensity = int(self.glow_row.get_value())
        self._apply()

    def _on_density_changed(self, *_a) -> None:
        self.settings.appearance.density = "compact" if self.density_row.get_active() else "comfortable"
        self._apply()

    def _on_remember_changed(self, *_a) -> None:
        self.settings.appearance.remember_window = self.remember_row.get_active()

    def _on_statusbar_changed(self, *_a) -> None:
        self.settings.appearance.show_status_bar = self.statusbar_row.get_active()
        if self.app.win:
            self.app.win.footer.set_visible(self.settings.appearance.show_status_bar)

    def _apply(self) -> None:
        self.app.apply_theme()
        self.settings.save()
