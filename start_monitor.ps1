# Claude Usage Monitor Starter für Windows
# Startet den Monitor über WSL mit aktivierter virtueller Umgebung

Write-Host "🚀 Claude Usage Monitor wird über WSL gestartet..." -ForegroundColor Green

# Wechsel ins Claude-Code Verzeichnis
$MonitorPath = "/mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor"

# Parameter an WSL weiterleiten
$WSLArgs = $args -join " "

if ($WSLArgs) {
    Write-Host "📝 Parameter: $WSLArgs" -ForegroundColor Yellow
    $Command = "cd '$MonitorPath' && ./start_monitor.sh $WSLArgs"
} else {
    $Command = "cd '$MonitorPath' && ./start_monitor.sh"
}

# Monitor über WSL starten
wsl -- bash -c $Command
