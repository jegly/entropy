# Entropy GUI

A GTK4 + libadwaita desktop front-end for [jegly/entropy](https://github.com/jegly/entropy),
the cryptographically-secure random data generator. Built for Ubuntu, styled
after [jegly/Tesseract](https://github.com/jegly/Tesseract) -- same palette
engine (Dracula, Catppuccin x4, Vintage Light, Neon Tessera, and a dozen
Gogh-derived terminal themes), same card/chip/pill visual language.

The GUI never re-implements the generator. It vendors the upstream
`entropy.py` unmodified, builds an argument list from the form, and runs it
as a subprocess -- reading its live progress bar, log output, and analysis
results back into the window.

## Features

- Size + unit picker, format (binary / text / image / audio)
- Entropy source: crypto-secure (default), fast (non-crypto), or mixed
  (adds hardware RNG, system noise, microphone, camera)
- Live progress bar with written/speed/ETA, cancellable mid-run
- Shannon entropy analysis (level bar), byte-frequency heatmap preview,
  hexdump, benchmark, and system entropy pool status
- Scrollable raw output log
- 20 built-in themes with live accent-color override, ported straight from
  Tesseract's theme engine
- Settings persisted at `~/.config/entropy-gui/settings.json`

## What's intentionally left out

`entropy.py --man` documents several flags (`--encrypt`, `--shred`,
`--watch`, `--chaos`, `--diff`, `--pattern`, `--corrupt`, `--quiet`,
`--split-into`, `-yes`/`-no-install`, `--entropy-source`) that are parsed by
argparse but not actually wired up to any behavior in the current upstream
script. The GUI doesn't expose controls for them -- a button that silently
does nothing is worse than no button. `--interactive` (mouse/keyboard timing
entropy) is also omitted since it needs a real terminal stdin, which a GUI
subprocess doesn't have. `--stream` (stdout piping) doesn't make sense
outside a shell pipeline either.

Two upstream quirks worth knowing, both reflected in the UI as disabled
controls with explanatory subtitles:

- `--seed` only affects `--fast` mode. Crypto and Mixed sources always read
  from the OS and ignore the Python-level seed.
- `--lorem` only has an effect when `--markov` is also enabled -- the
  character-by-character text generator never consults the word lists.

The GUI always passes `-force`, since it owns file naming/destination and a
headless subprocess can't answer entropy.py's interactive
overwrite-confirmation prompt.

## Install (Ubuntu)

Requires GTK4 + libadwaita GObject-introspection bindings (present by
default on recent Ubuntu/GNOME):

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

Then, from this directory:

```bash
./packaging/install.sh            # user-scope, installs to ~/.local
sudo ./packaging/install.sh --system   # system-wide, under /usr/local
```

This installs the `entropy-gui` launcher, the `.desktop` entry, and the
app icon. Launch it from your app grid as **Entropy**, or run `entropy-gui`.

Prefer a real `.deb` (declares `Depends:` so `apt` resolves the GTK4/
libadwaita bindings itself instead of the install script checking them)?

```bash
./packaging/build-deb.sh
sudo apt install ./entropy-gui_1.0.0_all.deb
```

## Run without installing

```bash
python3 -m entropy_gui
```

(run from this directory, or with it on `PYTHONPATH`)

## Layout

```
entropy_gui/
  app.py          main window, cards, generation flow
  theme.py        palette definitions + CSS compiler (ported from Tesseract)
  preferences.py  appearance settings window
  config.py       settings persistence
  runner.py       subprocess wrapper with live progress parsing
  vendor/
    entropy.py    snapshot of ../../entropy.py, unmodified -- kept so the
                  GUI (and its .deb) is self-contained and installable on
                  its own without the rest of this repo. Keep it in sync
                  with the top-level entropy.py when that changes.
packaging/
  install.sh              user-scope or --system install
  build-deb.sh             builds entropy-gui_<version>_all.deb
  com.jegly.entropygui.desktop
  debian/                  control/postinst/postrm/copyright for the .deb
  icons/hicolor/256x256/apps/com.jegly.entropygui.png
```

## Credits

- [jegly/entropy](https://github.com/jegly/entropy) -- the generator itself (MIT)
- [jegly/Tesseract](https://github.com/jegly/Tesseract) -- theme engine and
  visual language this GUI borrows from
