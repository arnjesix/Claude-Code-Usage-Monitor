#!/bin/bash
# Claude Usage Monitor Starter Script - Optimiert für Claude Pro
# Aktiviert automatisch die virtuelle Umgebung und startet den Monitor

# Verzeichnis des Scripts ermitteln
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Claude Pro Usage Monitor wird gestartet..."
echo "📂 Verzeichnis: $SCRIPT_DIR"

# Virtuelle Umgebung aktivieren
echo "🔄 Aktiviere virtuelle Umgebung..."
source "$SCRIPT_DIR/venv/bin/activate"

# Python-Version anzeigen
echo "🐍 Python-Version: $(python --version)"

# Claude Pro optimierte Defaults falls keine Parameter übergeben
if [ $# -eq 0 ]; then
    echo "📊 Nutze Claude Pro Standardkonfiguration..."
    python "$SCRIPT_DIR/ccusage_monitor.py" --plan pro --timezone Europe/Berlin
else
    echo "📊 Starte Monitor mit Custom-Parametern..."
    python "$SCRIPT_DIR/ccusage_monitor.py" "$@"
fi
