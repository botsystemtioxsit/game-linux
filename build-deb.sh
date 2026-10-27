#!/bin/sh
# Сборка пакета .deb для Debian / Ubuntu / Linux Mint.
# Результат: dist/solitaire-linux_<версия>_all.deb
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$SRC/solitaire/__init__.py")"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

PKG="$BUILD/solitaire-linux"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/share/solitaire-linux" "$PKG/usr/bin" \
         "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/256x256/apps" \
         "$PKG/usr/share/icons/hicolor/scalable/apps"
cp -r "$SRC/solitaire" "$SRC/data" "$PKG/usr/share/solitaire-linux/"
find "$PKG" -name "__pycache__" -type d -prune -exec rm -rf {} +
printf '#!/bin/sh\ncd /usr/share/solitaire-linux && exec /usr/bin/python3 -B -m solitaire "$@"\n' > "$PKG/usr/bin/solitaire-linux"
chmod 755 "$PKG/usr/bin/solitaire-linux"
cp "$SRC/data/solitaire-linux.desktop" "$PKG/usr/share/applications/"
[ -f "$SRC/data/solitaire-linux.png" ] && cp "$SRC/data/solitaire-linux.png" "$PKG/usr/share/icons/hicolor/256x256/apps/"
[ -f "$SRC/data/solitaire-linux.svg" ] && cp "$SRC/data/solitaire-linux.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/"

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: solitaire-linux
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-tk
Maintainer: solitaire-linux <noreply@example.com>
Description: Классический пасьянс «Косынка» (Klondike)
 Карточная игра с перетаскиванием карт мышью, отменой ходов,
 сдачей по 1 или 3 карты, подсчётом очков и статистикой.
CONTROL

chmod -R u+rwX,go+rX,go-w "$PKG"
mkdir -p "$SRC/dist"
dpkg-deb --root-owner-group --build "$PKG" "$SRC/dist/solitaire-linux_${VERSION}_all.deb"
