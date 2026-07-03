"""Theme engine, ported from jegly/Tesseract's theme.rs: palette manifests
compiled into GTK CSS through a user-priority CssProvider, layered over
libadwaita's StyleManager light/dark base.

Built-ins mirror Tesseract's set (Dracula, Catppuccin x4, Vintage Light,
Neon Tessera, plus the Gogh-derived terminal palettes) so Entropy's GUI
feels like a sibling app, not a stranger.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Palette:
    id: str
    name: str
    dark: bool = False
    follow_system: bool = False

    window_bg: str = ""
    view_bg: str = ""
    surface: str = ""
    surface_alt: str = ""
    headerbar: str = ""
    sidebar: str = ""
    card: str = ""
    popover: str = ""
    text: str = ""
    text_dim: str = ""
    accent: str = ""
    accent_fg: str = ""
    accent2: str = ""
    success: str = ""
    warning: str = ""
    error: str = ""
    border: str = ""

    radius: int = 12
    glow: bool = False
    serif: bool = False


def _p(id, name, *, dark, win, view, surface, alt, header, side, card, pop,
       text, dim, accent, accent_fg, accent2, ok, warn, err, border,
       radius=12, glow=False, serif=False) -> Palette:
    return Palette(
        id=id, name=name, dark=dark, follow_system=False,
        window_bg=win, view_bg=view, surface=surface, surface_alt=alt,
        headerbar=header, sidebar=side, card=card, popover=pop,
        text=text, text_dim=dim, accent=accent, accent_fg=accent_fg,
        accent2=accent2, success=ok, warning=warn, error=err, border=border,
        radius=radius, glow=glow, serif=serif,
    )


def builtin_themes() -> list[Palette]:
    return [
        Palette(id="follow-system", name="Follow System", follow_system=True),
        _p("dracula", "Dracula", dark=True,
           win="#282a36", view="#21222c", surface="#343746", alt="#3c3f51",
           header="#21222c", side="#262833", card="#313342", pop="#343746",
           text="#f8f8f2", dim="#9ea8c7",
           accent="#bd93f9", accent_fg="#1c1d26", accent2="#ff79c6",
           ok="#50fa7b", warn="#f1fa8c", err="#ff5555", border="#44475a"),
        _p("catppuccin-latte", "Catppuccin Latte", dark=False,
           win="#eff1f5", view="#ffffff", surface="#e6e9ef", alt="#dce0e8",
           header="#e6e9ef", side="#e9ecf2", card="#ffffff", pop="#eff1f5",
           text="#4c4f69", dim="#6c6f85",
           accent="#8839ef", accent_fg="#ffffff", accent2="#ea76cb",
           ok="#40a02b", warn="#df8e1d", err="#d20f39", border="#ccd0da"),
        _p("catppuccin-frappe", "Catppuccin Frappé", dark=True,
           win="#303446", view="#292c3c", surface="#414559", alt="#51576d",
           header="#292c3c", side="#2e3244", card="#3b3f54", pop="#414559",
           text="#c6d0f5", dim="#a5adce",
           accent="#ca9ee6", accent_fg="#232634", accent2="#f4b8e4",
           ok="#a6d189", warn="#e5c890", err="#e78284", border="#51576d"),
        _p("catppuccin-macchiato", "Catppuccin Macchiato", dark=True,
           win="#24273a", view="#1e2030", surface="#363a4f", alt="#494d64",
           header="#1e2030", side="#222539", card="#2f3247", pop="#363a4f",
           text="#cad3f5", dim="#a5adcb",
           accent="#c6a0f6", accent_fg="#181926", accent2="#f5bde6",
           ok="#a6da95", warn="#eed49f", err="#ed8796", border="#494d64"),
        _p("catppuccin-mocha", "Catppuccin Mocha", dark=True,
           win="#1e1e2e", view="#181825", surface="#313244", alt="#45475a",
           header="#181825", side="#1c1c2c", card="#2a2a3c", pop="#313244",
           text="#cdd6f4", dim="#a6adc8",
           accent="#cba6f7", accent_fg="#11111b", accent2="#f5c2e7",
           ok="#a6e3a1", warn="#f9e2af", err="#f38ba8", border="#45475a"),
        _p("vintage-light", "Vintage Light", dark=False,
           win="#f6efe1", view="#fbf6ea", surface="#efe5d0", alt="#e7dabf",
           header="#efe5d0", side="#f1e9d7", card="#fbf6ea", pop="#f3ecdc",
           text="#46392b", dim="#7a6a55",
           accent="#b07d3a", accent_fg="#fff8ec", accent2="#4f7c74",
           ok="#5f7d4f", warn="#b07d3a", err="#a14d3a", border="#d8c8a8",
           radius=14, serif=True),
        _p("neon-tessera", "Neon Tessera", dark=True,
           win="#0a0e14", view="#070a10", surface="#11161f", alt="#161d29",
           header="#0a0e14", side="#0d1118", card="#10151e", pop="#131923",
           text="#d8e6f2", dim="#7e93a8",
           accent="#00e5ff", accent_fg="#03131a", accent2="#ff2ec4",
           ok="#00ff9c", warn="#ffc400", err="#ff3860", border="#1d2735",
           radius=10, glow=True),
        # --- terminal / editor schemes (Gogh-derived palettes) ---
        _p("adventure-time", "Adventure Time", dark=True,
           win="#1f1d45", view="#17152f", surface="#2a2755", alt="#34306a",
           header="#17152f", side="#1b1940", card="#252253", pop="#2a2755",
           text="#f8dcc0", dim="#a39ac4",
           accent="#e7741e", accent_fg="#1f1d45", accent2="#5cf9ff",
           ok="#4ab118", warn="#e7b000", err="#bd0013", border="#3a356f"),
        _p("borland", "Borland", dark=True,
           win="#0000a4", view="#000084", surface="#0a1ab0", alt="#1730c0",
           header="#000084", side="#00118f", card="#0817ac", pop="#0a1ab0",
           text="#ffff80", dim="#b6b6e6",
           accent="#ffff4e", accent_fg="#0000a4", accent2="#4fe9fc",
           ok="#4efa78", warn="#ffff4e", err="#ff5959", border="#2a40c4",
           radius=8),
        _p("c64", "Commodore 64", dark=True,
           win="#40318d", view="#352978", surface="#4d3ea0", alt="#5a4bb0",
           header="#352978", side="#3a2e85", card="#473a98", pop="#4d3ea0",
           text="#cabdf2", dim="#9385c9",
           accent="#bfce72", accent_fg="#40318d", accent2="#67b6bd",
           ok="#55a049", warn="#bfce72", err="#883932", border="#5648a8",
           radius=8),
        _p("fairy-floss-dark", "Fairy Floss Dark", dark=True,
           win="#3b364c", view="#332f42", surface="#4a4564", alt="#56506f",
           header="#332f42", side="#3d3850", card="#453f5c", pop="#4a4564",
           text="#f8f8f2", dim="#c5bdda",
           accent="#ffb8d1", accent_fg="#3b364c", accent2="#c5a3ff",
           ok="#c2ffdf", warn="#ffea00", err="#ff857f", border="#564f6f",
           radius=14),
        _p("flat", "Flat", dark=True,
           win="#2c3e50", view="#243342", surface="#34495e", alt="#3e5870",
           header="#243342", side="#2a3a4a", card="#324356", pop="#34495e",
           text="#ecf0f1", dim="#a4b5c4",
           accent="#3498db", accent_fg="#ffffff", accent2="#9b59b6",
           ok="#2ecc71", warn="#f1c40f", err="#e74c3c", border="#3e5066"),
        _p("gogh", "Gogh — Starry Night", dark=True,
           win="#0d1b34", view="#0a1628", surface="#14264a", alt="#1b3260",
           header="#0a1628", side="#0f1d38", card="#122243", pop="#14264a",
           text="#e8eeff", dim="#94a8cc",
           accent="#f4cd3a", accent_fg="#0d1b34", accent2="#5b8dd9",
           ok="#6bbf59", warn="#f4cd3a", err="#d9603b", border="#21345f"),
        _p("grass", "Grass", dark=True,
           win="#13773d", view="#0f6234", surface="#1c8a4a", alt="#239a55",
           header="#0f6234", side="#126b38", card="#188044", pop="#1c8a4a",
           text="#fff0a5", dim="#bcd6a0",
           accent="#e7b000", accent_fg="#13773d", accent2="#7fd9b0",
           ok="#9bea6a", warn="#e7b000", err="#cf3a2a", border="#2a9a5e"),
        _p("gruvbox-material", "Gruvbox Material", dark=True,
           win="#282828", view="#1f1f1f", surface="#32302f", alt="#3c3836",
           header="#1f1f1f", side="#252423", card="#2f2d2c", pop="#32302f",
           text="#d4be98", dim="#a89984",
           accent="#d8a657", accent_fg="#282828", accent2="#7daea3",
           ok="#a9b665", warn="#d8a657", err="#ea6962", border="#45403d"),
        _p("homebrew", "Homebrew", dark=True,
           win="#000000", view="#050505", surface="#0c140c", alt="#122012",
           header="#000000", side="#040804", card="#0a120a", pop="#0c140c",
           text="#00d000", dim="#1f8a1f",
           accent="#00ff00", accent_fg="#001500", accent2="#00d8b2",
           ok="#00c800", warn="#9a9a00", err="#c80000", border="#103810",
           radius=8, glow=True),
        _p("ocean", "Ocean", dark=True,
           win="#2b303b", view="#232831", surface="#343d46", alt="#3e4855",
           header="#232831", side="#2a2f39", card="#313844", pop="#343d46",
           text="#c0c5ce", dim="#8b95a4",
           accent="#8fa1b3", accent_fg="#1b2027", accent2="#b48ead",
           ok="#a3be8c", warn="#ebcb8b", err="#bf616a", border="#3e4855"),
        _p("kokuban", "Kokuban", dark=True,
           win="#1f3526", view="#192c1f", surface="#274030", alt="#2f4c39",
           header="#192c1f", side="#1d3123", card="#243c2d", pop="#274030",
           text="#f0f0e8", dim="#a9c2af",
           accent="#f2e9c8", accent_fg="#1f3526", accent2="#f2b4b4",
           ok="#a8d8a0", warn="#f0e68c", err="#f2a0a0", border="#315040"),
        _p("mono-cyan", "Mono Cyan", dark=True,
           win="#081414", view="#040e0e", surface="#0e1f1f", alt="#143030",
           header="#040e0e", side="#0a1818", card="#0c1c1c", pop="#0e1f1f",
           text="#c8f0f0", dim="#5c9a9a",
           accent="#00d0d0", accent_fg="#021616", accent2="#5ce0e0",
           ok="#00d0a0", warn="#80e0e0", err="#e08585", border="#163838",
           radius=10, glow=True),
    ]


def find_theme(theme_id: str) -> Palette:
    for p in builtin_themes():
        if p.id == theme_id:
            return p
    return builtin_themes()[0]


def _alpha(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"alpha(currentColor, {a})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {a:.2f})"


def compile_css(p: Palette, accent_override: str, glow_intensity: int,
                 density: str, font: str) -> str:
    """Compile a palette + user preferences into GTK CSS."""
    css = []
    accent = accent_override if (len(accent_override) == 7 and accent_override.startswith("#")) else p.accent

    if not p.follow_system:
        css.append(f""":root {{
  --window-bg-color: {p.window_bg};
  --window-fg-color: {p.text};
  --view-bg-color: {p.view_bg};
  --view-fg-color: {p.text};
  --headerbar-bg-color: {p.headerbar};
  --headerbar-fg-color: {p.text};
  --headerbar-backdrop-color: {p.window_bg};
  --sidebar-bg-color: {p.sidebar};
  --sidebar-fg-color: {p.text};
  --sidebar-backdrop-color: {p.window_bg};
  --secondary-sidebar-bg-color: {p.sidebar};
  --secondary-sidebar-fg-color: {p.text};
  --card-bg-color: {p.card};
  --card-fg-color: {p.text};
  --dialog-bg-color: {p.surface};
  --dialog-fg-color: {p.text};
  --popover-bg-color: {p.popover};
  --popover-fg-color: {p.text};
  --success-color: {p.success};
  --success-bg-color: {p.success};
  --success-fg-color: {p.accent_fg};
  --warning-color: {p.warning};
  --warning-bg-color: {p.warning};
  --warning-fg-color: {p.accent_fg};
  --error-color: {p.error};
  --error-bg-color: {p.error};
  --error-fg-color: {p.accent_fg};
  --destructive-color: {p.error};
  --destructive-bg-color: {p.error};
  --destructive-fg-color: {p.accent_fg};
}}""")
    if accent:
        afg = p.accent_fg or "#ffffff"
        css.append(f""":root {{
  --accent-bg-color: {accent};
  --accent-fg-color: {afg};
  --accent-color: {accent};
}}""")

    radius = p.radius
    shadow = ("0 1px 3px rgba(0,0,0,0.42), 0 4px 14px rgba(0,0,0,0.28)" if p.dark
              else "0 1px 3px rgba(60,50,40,0.10), 0 4px 16px rgba(60,50,40,0.08)")
    border = p.border or "alpha(currentColor, 0.12)"
    chipbg = _alpha(p.text_dim or "#888888", 0.18)
    dimbg = _alpha(p.text_dim or "#888888", 0.14)
    okbg = _alpha(p.success or "#2ec27e", 0.16)
    ok = p.success or "var(--success-color)"
    warnbg = _alpha(p.warning or "#e5a50a", 0.16)
    warn = p.warning or "var(--warning-color)"
    errbg = _alpha(p.error or "#e01b24", 0.16)
    errbg2 = _alpha(p.error or "#e01b24", 0.12)
    err40 = _alpha(p.error or "#e01b24", 0.4)
    err = p.error or "var(--error-color)"
    dim = p.text_dim or "alpha(currentColor, 0.6)"
    dropbg = _alpha(p.surface_alt or "#808080", 0.25)
    accent_css = accent or "var(--accent-bg-color)"
    acc06 = _alpha(accent or "#3584e4", 0.07)
    acc10 = _alpha(accent or "#3584e4", 0.10)
    acc20 = _alpha(accent or "#3584e4", 0.20)
    a210 = _alpha(p.accent2 or "#3584e4", 0.10)
    a2solid = p.accent2 or "var(--accent-color)"
    a2line = _alpha(p.accent2 or "#3584e4", 0.55)

    css.append(f"""
.card, .ent-card, preferencesgroup > box > listbox.boxed-list {{
  border-radius: {radius}px;
}}
.ent-card {{
  background-color: var(--card-bg-color);
  box-shadow: {shadow};
  border: 1px solid {border};
  padding: 4px;
}}
.ent-elevated {{ box-shadow: {shadow}; }}
button.pill {{ border-radius: 999px; padding-left: 22px; padding-right: 22px; }}
button {{ border-radius: 10px; }}
entry, spinbutton {{ border-radius: 10px; }}
.boxed-list {{ border-radius: {radius}px; }}
.ent-chip {{
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.82em;
  font-weight: 600;
  background-color: {chipbg};
  color: var(--window-fg-color);
}}
.ent-chip.running {{ background-color: {okbg}; color: {ok}; }}
.ent-chip.idle {{ background-color: {dimbg}; }}
.ent-chip.busy {{ background-color: {warnbg}; color: {warn}; }}
.ent-chip.danger {{ background-color: {errbg}; color: {err}; }}
.ent-dim {{ color: {dim}; }}
.ent-mono {{ font-family: monospace; font-size: 0.88em; color: {a2solid}; }}
.ent-statusbar {{
  border-top: 1px solid {border};
  padding: 6px 14px;
  background-color: var(--headerbar-bg-color);
}}
.ent-hero {{ font-weight: 800; font-size: 1.7em; color: {accent_css}; }}
.ent-section-title {{ font-weight: 700; font-size: 1.06em; color: {a2solid}; }}
levelbar block.filled {{ background-color: {accent_css}; }}
levelbar block.high {{ background-color: {ok}; }}
levelbar block.low {{ background-color: {warn}; }}
progressbar progress {{ background-color: {a2solid}; }}
checkbutton check:checked, checkbutton radio:checked {{ background-color: {a2solid}; }}
.ent-card {{ border-top: 2px solid {a2line}; }}
spinner {{ color: {accent_css}; }}
switch:checked {{ background-color: {accent_css}; }}
.ent-drop-zone {{
  border: 2px dashed {border};
  border-radius: {radius}px;
  padding: 28px;
  background-color: {dropbg};
  transition: border-color 160ms ease, background-color 160ms ease;
}}
.ent-help {{
  border-radius: {radius}px;
  padding: 10px 12px;
  background-color: {acc10};
  border: 1px solid {acc20};
}}
.ent-help label {{ font-size: 0.92em; }}
button.ent-panic {{
  border-radius: 999px;
  font-weight: 700;
  background-color: {errbg2};
  color: {err};
  border: 1px solid {err40};
}}
button.ent-panic:hover {{ background-color: {err}; color: #ffffff; }}
.ent-pad {{
  border-radius: {radius}px;
  background: linear-gradient(135deg, {acc10}, {a210});
  border: 1px solid {border};
}}
""")

    if p.glow:
        g = min(glow_intensity, 100) / 100.0
        acc = accent or p.accent
        r1 = int(10 + 14 * g)
        r2 = int(6 + 10 * g)
        a1 = _alpha(acc, 0.10 + 0.10 * g)
        a2 = _alpha(acc, 0.25 + 0.25 * g)
        a25 = _alpha(acc, 0.25)
        a35 = _alpha(acc, 0.30)
        a45 = _alpha(acc, 0.45)
        okglow = _alpha(p.success, 0.5)
        errglow = _alpha(p.error, 0.35)
        css.append(f"""
.ent-card {{
  box-shadow: 0 0 {r1}px {a1}, 0 1px 3px rgba(0,0,0,0.5);
  border: 1px solid {a35};
}}
button.suggested-action {{
  box-shadow: 0 0 {r2}px {a2};
  text-shadow: 0 0 6px {a2};
}}
headerbar {{ border-bottom: 1px solid {a25}; }}
.ent-hero {{ color: {acc}; text-shadow: 0 0 12px {a45}; }}
.ent-chip.running {{ box-shadow: 0 0 8px {okglow}; }}
button.ent-panic {{ box-shadow: 0 0 {r2}px {errglow}; }}
.ent-statusbar {{ border-top: 1px solid {a25}; }}
levelbar block.filled {{ background-color: {acc}; box-shadow: 0 0 6px {a45}; }}
""")

    if p.serif:
        css.append("""
.ent-dim, .ent-help label {
  font-family: "Source Serif Pro", "Noto Serif", "Georgia", serif;
}
""")

    css.append("""
.ent-hero, .ent-section-title, .heading,
windowtitle > .title, window > headerbar .title,
.title-1, .title-2, .title-3, .title-4 {
  letter-spacing: 0.3px;
}
""")

    if density == "compact":
        css.append("""
listbox row { min-height: 30px; }
headerbar { min-height: 38px; }
button { padding-top: 2px; padding-bottom: 2px; }
""")

    if font:
        css.append(f'window {{ font-family: "{font}"; }}\n')

    return "\n".join(css)
