"""Settings persistence: ~/.config/entropy-gui/settings.json"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "entropy-gui"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Appearance:
    theme: str = "follow-system"
    accent: str = ""
    density: str = "comfortable"
    glow_intensity: int = 60
    window_width: int = 880
    window_height: int = 760
    remember_window: bool = True
    show_status_bar: bool = True


@dataclass
class Defaults:
    output_dir: str = str(Path.home())
    format: str = "bin"
    source: str = "crypto"


@dataclass
class Settings:
    appearance: Appearance = field(default_factory=Appearance)
    defaults: Defaults = field(default_factory=Defaults)

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                app_fields = {f.name for f in fields(Appearance)}
                def_fields = {f.name for f in fields(Defaults)}
                appearance = Appearance(**{k: v for k, v in data.get("appearance", {}).items() if k in app_fields})
                defaults = Defaults(**{k: v for k, v in data.get("defaults", {}).items() if k in def_fields})
                return cls(appearance=appearance, defaults=defaults)
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({
            "appearance": asdict(self.appearance),
            "defaults": asdict(self.defaults),
        }, indent=2))
