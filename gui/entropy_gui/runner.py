"""Runs the vendored entropy.py CLI as a subprocess and streams its output
back to the GTK main loop.

entropy.py draws its progress bar with bare '\\r' (no newline) and only an
explicit sys.stdout.flush() after each chunk -- so a naive `for line in
proc.stdout` would block until the *whole* run produced a single '\\n'.
Instead we read raw characters and split on both '\\r' and '\\n' ourselves.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from gi.repository import GLib

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
ENTROPY_PY = VENDOR_DIR / "entropy.py"

_PROGRESS_RE = re.compile(
    r"\[(?P<bar>[█░]*)\]\s*(?P<percent>[\d.]+)%\s*\|\s*"
    r"(?P<written>[\d.]+\s*[A-Za-z]+)\s*\|\s*"
    r"(?P<speed>[\d.]+\s*[A-Za-z]+)/s\s*\|\s*ETA:\s*(?P<eta>\d+)s"
)

# Exit codes documented by `entropy.py --man`.
EXIT_MESSAGES = {
    0: "Done",
    1: "General error (invalid arguments or permissions)",
    2: "Missing dependencies",
    3: "Disk full or insufficient space",
    4: "Interrupted",
}


class GenerationJob:
    def __init__(
        self,
        args: list[str],
        cwd: str,
        on_progress: Callable[[float, str, str, int], None],
        on_line: Callable[[str], None],
        on_done: Callable[[int, bool], None],
    ):
        self.args = args
        self.cwd = cwd
        self.on_progress = on_progress
        self.on_line = on_line
        self.on_done = on_done
        self.proc: subprocess.Popen | None = None
        self._cancelled = False

    def command_preview(self) -> str:
        return "entropy.py " + " ".join(self.args)

    def start(self) -> None:
        cmd = [sys.executable, "-u", str(ENTROPY_PY), *self.args]
        self.proc = subprocess.Popen(
            cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        # Some option combos (Mixed source + per-byte text generation) are
        # CPU-bound single-core hogs in entropy.py itself; niceing the child
        # from the parent (not preexec_fn, which Python's own docs warn is
        # unsafe to combine with threads) keeps it from starving the
        # GUI/compositor and looking like a hang. Doesn't change the data.
        try:
            os.setpriority(os.PRIO_PROCESS, self.proc.pid, 15)
        except OSError:
            pass
        threading.Thread(target=self._pump, daemon=True).start()

    def cancel(self) -> None:
        if self.proc and self.proc.poll() is None:
            self._cancelled = True
            self.proc.terminate()

    def _pump(self) -> None:
        assert self.proc is not None
        stream = self.proc.stdout
        buf = []
        try:
            while True:
                ch = stream.read(1)
                if ch == "":
                    break
                if ch in ("\r", "\n"):
                    if buf:
                        self._emit("".join(buf))
                        buf.clear()
                else:
                    buf.append(ch)
        finally:
            if buf:
                self._emit("".join(buf))
            code = self.proc.wait()
            GLib.idle_add(self.on_done, code, self._cancelled)

    def _emit(self, line: str) -> None:
        m = _PROGRESS_RE.search(line)
        if m:
            GLib.idle_add(
                self.on_progress,
                float(m.group("percent")),
                m.group("written").replace(" ", ""),
                m.group("speed").replace(" ", ""),
                int(m.group("eta")),
            )
        else:
            GLib.idle_add(self.on_line, line)


def format_size_arg(value: float, unit: str) -> str:
    """entropy.py expects e.g. '-10gb'; only pre-processed if it matches
    ^-\\d+(\\.\\d+)?(kb|mb|gb|tb)$ so keep the numeric part plain."""
    if value == int(value):
        num = str(int(value))
    else:
        num = f"{value:g}"
    return f"-{num}{unit.lower()}"
