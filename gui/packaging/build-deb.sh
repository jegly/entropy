#!/usr/bin/env bash
# Builds entropy-gui_<version>_all.deb. This is a real Depends: declaration
# (python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1) -- unlike install.sh, which
# checks and offers to apt-install those itself, `apt install ./*.deb` will
# resolve and pull them in on its own.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG="entropy-gui"
ARCH="all"
VERSION="${1:-1.0.0}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

install -d "$STAGE/DEBIAN"
install -d "$STAGE/usr/bin"
install -d "$STAGE/usr/lib/entropy-gui"
install -d "$STAGE/usr/share/applications"
install -d "$STAGE/usr/share/icons/hicolor"
install -d "$STAGE/usr/share/doc/$PKG"

cp -r "$REPO_ROOT/entropy_gui" "$STAGE/usr/lib/entropy-gui/entropy_gui"
find "$STAGE/usr/lib/entropy-gui" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

cat > "$STAGE/usr/bin/entropy-gui" <<'LAUNCHER'
#!/usr/bin/env bash
exec env PYTHONPATH="/usr/lib/entropy-gui:${PYTHONPATH:-}" python3 -m entropy_gui "$@"
LAUNCHER
chmod 755 "$STAGE/usr/bin/entropy-gui"

install -m644 "$REPO_ROOT/packaging/com.jegly.entropygui.desktop" "$STAGE/usr/share/applications/"
cp -r "$REPO_ROOT/packaging/icons/hicolor/." "$STAGE/usr/share/icons/hicolor/"

install -m644 "$REPO_ROOT/packaging/debian/copyright" "$STAGE/usr/share/doc/$PKG/copyright"
install -m644 "$REPO_ROOT/README.md" "$STAGE/usr/share/doc/$PKG/README.md"

sed "s/@VERSION@/$VERSION/" "$REPO_ROOT/packaging/debian/control" > "$STAGE/DEBIAN/control"
install -m755 "$REPO_ROOT/packaging/debian/postinst" "$STAGE/DEBIAN/postinst"
install -m755 "$REPO_ROOT/packaging/debian/postrm" "$STAGE/DEBIAN/postrm"

find "$STAGE" -type d -exec chmod 755 {} +
find "$STAGE" -type f -not -path "*/DEBIAN/*" -exec chmod 644 {} +
chmod 755 "$STAGE/usr/bin/entropy-gui"

OUT="$REPO_ROOT/${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT"

echo
echo "Built: $OUT"
# The ./ is load-bearing: apt only treats an argument as a file path if it
# contains a slash, otherwise it hunts for a repo package by that name.
echo "Install with:   sudo apt install ./$(basename "$OUT")   (run from $REPO_ROOT)"
echo "Remove with:    sudo apt remove entropy-gui"
