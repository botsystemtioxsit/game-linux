#!/bin/sh
# Удаление «Косынки». Для системной установки: sudo ./uninstall.sh --system
set -e
if [ "$1" = "--system" ]; then
    PREFIX="${PREFIX:-/usr/local}"
else
    PREFIX="${PREFIX:-$HOME/.local}"
fi
rm -rf "$PREFIX/share/solitaire-linux"
rm -f "$PREFIX/bin/solitaire-linux" \
      "$PREFIX/share/applications/solitaire-linux.desktop" \
      "$PREFIX/share/icons/hicolor/256x256/apps/solitaire-linux.png" \
      "$PREFIX/share/icons/hicolor/scalable/apps/solitaire-linux.svg"
echo "«Косынка» удалена. Статистика осталась в ~/.config/solitaire-linux (можно удалить вручную)."
