#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 SYMBOL" >&2
    exit 1
fi

SYMBOL="${1^^}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UV="$(command -v uv)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/onetick-${SYMBOL}.desktop"

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=onetick ${SYMBOL}
Comment=Stock ticker for ${SYMBOL}
Exec=${UV} run ${SCRIPT_DIR}/onetick.py ${SYMBOL}
Type=Application
Terminal=false
Categories=Finance;
StartupNotify=false
EOF

chmod +x "$DESKTOP_FILE"
echo "Installed: $DESKTOP_FILE"
echo "Search for 'onetick ${SYMBOL}' in Activities to launch."
