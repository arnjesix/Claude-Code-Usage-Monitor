# Claude Usage Monitor - Installation erfolgreich! 🎉

## ✅ Was wurde installiert:

1. **Repository geklont**: Claude-Code-Usage-Monitor von GitHub
2. **Virtuelle Umgebung**: Python venv mit isolierten Abhängigkeiten
3. **Python-Abhängigkeiten**: pytz für Zeitzonenverwaltung
4. **Node.js Tool**: ccusage CLI global installiert
5. **Start-Scripts**: Sowohl für WSL als auch Windows PowerShell

## 🚀 Verwendung:

### Option 1: Über WSL (empfohlen)
```bash
# In WSL Terminal:
cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor
./start_monitor.sh
```

### Option 2: Über Windows PowerShell
```powershell
# In PowerShell von VS Code oder Windows Terminal:
cd "C:\Users\arnje\Documents\VS-Code\Claude-Code\Claude-Code-Usage-Monitor"
.\start_monitor.ps1
```

### Option 3: Direkter WSL-Aufruf
```bash
# Von überall aus Windows:
wsl -- bash -c "cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor && ./start_monitor.sh"
```

## 📊 Konfigurationsmöglichkeiten:

```bash
# Standard Pro Plan (7.000 tokens)
./start_monitor.sh

# Max5 Plan (35.000 tokens)
./start_monitor.sh --plan max5

# Max20 Plan (140.000 tokens)
./start_monitor.sh --plan max20

# Auto-Erkennung der Limits
./start_monitor.sh --plan custom_max

# Custom Reset-Zeit (z.B. 9 Uhr morgens)
./start_monitor.sh --reset-hour 9

# Deutsche Zeitzone
./start_monitor.sh --timezone Europe/Berlin

# Kombination der Optionen
./start_monitor.sh --plan max5 --reset-hour 8 --timezone Europe/Berlin
```

## 🎯 Integration mit Ihrem Claude Code:

Der Monitor läuft parallel zu Ihrem `start_claude.py` Script. Sie können beide gleichzeitig verwenden:

1. **Terminal 1**: Starten Sie den Monitor
2. **Terminal 2**: Verwenden Sie Ihr `start_claude.py` Script wie gewohnt

## 🔧 Virtuelle Umgebung Details:

- **Pfad**: `/mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor/venv`
- **Python Version**: 3.12.3
- **Installierte Pakete**: pytz-2025.2
- **Automatische Aktivierung**: Durch start_monitor.sh

## 🆘 Fehlerbehebung:

### Falls "No active session found":
1. Starten Sie Claude Code und senden mindestens 2 Nachrichten
2. Starten Sie dann den Monitor

### Falls Permissions-Fehler:
```bash
wsl -- bash -c "cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor && chmod +x *.sh *.py"
```

### Virtuelle Umgebung manuell aktivieren:
```bash
cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor
source venv/bin/activate
python ccusage_monitor.py
```

## 💡 Tipps:

1. **Alias erstellen**: Fügen Sie zu Ihrer `~/.bashrc` hinzu:
   ```bash
   alias claude-monitor='cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor && ./start_monitor.sh'
   ```

2. **VS Code Integration**: Öffnen Sie das Verzeichnis in VS Code für einfachen Zugriff

3. **Multiple Sessions**: Der Monitor erkennt überlappende Claude-Sessions automatisch

Viel Spaß mit dem Claude Usage Monitor! 🎊
