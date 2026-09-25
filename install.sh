#!/bin/sh
# Установка «Косынки».
#   ./install.sh           — для текущего пользователя (в ~/.local, без sudo)
#   sudo ./install.sh --system — для всех пользователей (в /usr/local)
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "--system" ]; then
    PREFIX="${PREFIX:-/usr/local}"
else
    PREFIX="${PREFIX:-$HOME/.local}"
fi

# Ищем Python 3, в котором есть tkinter (системный — в приоритете).
find_python() {
    for candidate in /usr/bin/python3 "$(command -v python3 2>/dev/null)"; do
        if [ -x "$candidate" ] && "$candidate" -c "import tkinter" 2>/dev/null; then
            echo "$candidate"
            return
        fi
    done
}

if ! command -v python3 >/dev/null 2>&1 && [ ! -x /usr/bin/python3 ]; then
    echo "Ошибка: не найден python3. Установите Python 3 через менеджер пакетов." >&2
    exit 1
fi

PYTHON="$(find_python)"
if [ -z "$PYTHON" ]; then
    echo "Не найден модуль tkinter (графика для Python)."
    if command -v apt-get >/dev/null 2>&1; then
        CMD="sudo apt-get install -y python3-tk"
    elif command -v dnf >/dev/null 2>&1; then
        CMD="sudo dnf install -y python3-tkinter"
    elif command -v pacman >/dev/null 2>&1; then
        CMD="sudo pacman -S --needed tk"
    elif command -v zypper >/dev/null 2>&1; then
        CMD="sudo zypper install -y python3-tk"
    else
        CMD=""
    fi
    if [ -n "$CMD" ]; then
        printf "Установить его командой «%s»? [Y/n] " "$CMD"
        read -r answer || answer=""
        case "$answer" in
            [nNнН]*) echo "Установка прервана."; exit 1 ;;
            *) $CMD ;;
        esac
    fi
    PYTHON="$(find_python)"
    if [ -z "$PYTHON" ]; then
        echo "Ошибка: tkinter по-прежнему недоступен. Установите пакет с tkinter для Python 3 вручную." >&2
        exit 1
    fi
fi

APPDIR="$PREFIX/share/solitaire-linux"
echo "Устанавливаю в $PREFIX ..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR" "$PREFIX/bin" "$PREFIX/share/applications" \
         "$PREFIX/share/icons/hicolor/256x256/apps" "$PREFIX/share/icons/hicolor/scalable/apps"
cp -r "$SRC/solitaire" "$SRC/data" "$APPDIR/"
find "$APPDIR" -name "__pycache__" -type d -prune -exec rm -rf {} +

cat > "$PREFIX/bin/solitaire-linux" <<LAUNCHER
#!/bin/sh
cd "$APPDIR" && exec "$PYTHON" -B -m solitaire "\$@"
LAUNCHER
chmod 755 "$PREFIX/bin/solitaire-linux"

sed "s|^Exec=.*|Exec=$PREFIX/bin/solitaire-linux|" "$SRC/data/solitaire-linux.desktop" \
    > "$PREFIX/share/applications/solitaire-linux.desktop"
cp "$SRC/data/solitaire-linux.png" "$PREFIX/share/icons/hicolor/256x256/apps/"
cp "$SRC/data/solitaire-linux.svg" "$PREFIX/share/icons/hicolor/scalable/apps/"

command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -q -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true

echo "Готово! «Косынка» появилась в меню приложений (раздел «Игры»)."
echo "Запуск из терминала: $PREFIX/bin/solitaire-linux"
