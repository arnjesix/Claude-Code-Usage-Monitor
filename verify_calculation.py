#!/usr/bin/env python3
"""
Verifizierung der Session-Token-Berechnung
"""

import subprocess
import json
from datetime import datetime, timezone

def run_wsl_command(command):
    """WSL-Befehl ausführen."""
    try:
        result = subprocess.run(
            ['wsl', 'bash', '-c', command],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='ignore'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    print("=== VERIFIKATION DER SESSION-TOKEN-BERECHNUNG ===")
    print()
    
    # 1. Aktuelle Gesamttokens abrufen
    code, stdout, stderr = run_wsl_command('ccusage session --json')
    if code == 0:
        try:
            data = json.loads(stdout)
            current_total = data.get('totals', {}).get('totalTokens', 0)
            print(f"Aktuelle Gesamttokens: {current_total:,}")
        except:
            current_total = 0
            print("Fehler beim Abrufen der Gesamttokens")
    else:
        current_total = 0
        print("Fehler beim Ausführen von ccusage session")
    
    # 2. Heutige Tokens abrufen
    code, stdout, stderr = run_wsl_command('ccusage daily --json')
    if code == 0:
        try:
            data = json.loads(stdout)
            today_tokens = 0
            for day in data.get('days', []):
                if day.get('date') == '2025-06-27':
                    today_tokens = day.get('totalTokens', 0)
                    break
            print(f"Heutige Tokens (2025-06-27): {today_tokens:,}")
        except:
            today_tokens = 0
            print("Fehler beim Parsen der täglichen Daten")
    else:
        today_tokens = 0
        print("Fehler beim Ausführen von ccusage daily")
    
    # 3. Session-Daten laden
    try:
        with open('session_state.json', 'r') as f:
            session_data = json.load(f)
        
        session_start_time = session_data.get('session_start_time')
        session_start_tokens = session_data.get('session_start_tokens', 0)
        
        print(f"Session Start Zeit: {session_start_time}")
        print(f"Session Start Tokens: {session_start_tokens:,}")
        
    except Exception as e:
        print(f"Fehler beim Laden der Session-Daten: {e}")
        session_start_tokens = 0
        session_start_time = None
    
    # 4. Berechnungen durchführen
    print("\n=== BERECHNUNGEN ===")
    
    # Berechnung 1: Session-Tokens basierend auf aktuellen Daten
    calculated_session_tokens = current_total - session_start_tokens
    print(f"Berechnete Session-Tokens: {current_total:,} - {session_start_tokens:,} = {calculated_session_tokens:,}")
    
    # Berechnung 2: Vergleich mit heutigen Tokens
    print(f"Heutige Tokens: {today_tokens:,}")
    
    # Berechnung 3: Korrekte session_start_tokens
    correct_session_start_tokens = current_total - today_tokens
    print(f"Korrekte session_start_tokens: {current_total:,} - {today_tokens:,} = {correct_session_start_tokens:,}")
    
    # 5. Session-Dauer
    if session_start_time:
        try:
            session_start = datetime.fromisoformat(session_start_time)
            now = datetime.now(timezone.utc)
            duration = now - session_start
            hours = duration.total_seconds() / 3600
            
            print(f"\nSession-Dauer: {duration} ({hours:.2f} Stunden)")
            
            if today_tokens > 0:
                tokens_per_hour = today_tokens / hours
                print(f"Durchschnittliche Tokens pro Stunde: {tokens_per_hour:,.0f}")
            
        except Exception as e:
            print(f"Fehler bei Session-Dauer-Berechnung: {e}")
    
    # 6. Validierung
    print("\n=== VALIDIERUNG ===")
    
    if session_start_tokens == correct_session_start_tokens:
        print("✓ session_start_tokens sind KORREKT")
    else:
        print(f"✗ session_start_tokens sind FALSCH")
        print(f"  Aktuell: {session_start_tokens:,}")
        print(f"  Korrekt: {correct_session_start_tokens:,}")
        print(f"  Differenz: {abs(session_start_tokens - correct_session_start_tokens):,}")
    
    if calculated_session_tokens == today_tokens:
        print("✓ Session-Tokens entsprechen heutigen Tokens")
    else:
        print(f"✗ Session-Tokens weichen ab")
        print(f"  Berechnet: {calculated_session_tokens:,}")
        print(f"  Heute: {today_tokens:,}")
        print(f"  Differenz: {abs(calculated_session_tokens - today_tokens):,}")
    
    # 7. Zusammenfassung
    print("\n=== ZUSAMMENFASSUNG ===")
    print(f"Session-Tokens (heute): {today_tokens:,}")
    print(f"Korrekte session_start_tokens: {correct_session_start_tokens:,}")
    
    if today_tokens >= 1000000:
        print(f"✓ Session-Tokens sind im Millionen-Bereich wie erwartet")
    else:
        print(f"✗ Session-Tokens sind zu niedrig")
    
    return today_tokens, correct_session_start_tokens

if __name__ == "__main__":
    main()