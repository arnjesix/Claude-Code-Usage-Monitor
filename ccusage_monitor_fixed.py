#!/usr/bin/env python3
"""
Fixed Claude Token Monitor - Works both in Windows and WSL
Automatically detects environment and uses appropriate ccusage command
"""

import subprocess
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz
import shutil
from collections import defaultdict
import math

def is_running_in_wsl():
    """Check if the script is running inside WSL."""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower() or 'wsl' in f.read().lower()
    except FileNotFoundError:
        return False

def check_ccusage_availability():
    """Check if ccusage command is available on the system."""
    return shutil.which('ccusage') is not None

def run_ccusage():
    """Execute ccusage blocks --json command and return parsed JSON data."""
    try:
        if is_running_in_wsl():
            # Running in WSL - use ccusage directly
            result = subprocess.run(
                ['ccusage', 'blocks', '--json'],
                capture_output=True,
                text=True,
                timeout=15
            )
        else:
            # Running in Windows - use WSL
            result = subprocess.run(
                ['wsl', 'bash', '-c', 'ccusage blocks --json'],
                capture_output=True,
                text=True,
                timeout=15
            )
        
        if result.returncode != 0:
            print(f"❌ ccusage error: {result.stderr}")
            return None
            
        return json.loads(result.stdout)
        
    except subprocess.TimeoutExpired:
        print("❌ ccusage command timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON output from ccusage: {e}")
        return None
    except FileNotFoundError:
        if is_running_in_wsl():
            print("❌ ccusage not found in WSL. Please install ccusage.")
        else:
            print("❌ WSL not found. Please install Windows Subsystem for Linux.")
        return None
    except Exception as e:
        print(f"❌ Unexpected error running ccusage: {e}")
        return None

def create_token_progress_bar(percentage, width=50):
    """Create a token usage progress bar with bracket style."""
    filled = int(width * percentage / 100)
    
    # Create the bar with green fill and red empty space
    green_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    green = '\033[92m'  # Bright green
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    return f"🟢 [{green}{green_bar}{red}{red_bar}{reset}] {percentage:.1f}%"


def create_time_progress_bar(elapsed_minutes, total_minutes, width=50):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with blue fill and red empty space
    blue_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    blue = '\033[94m'   # Bright blue
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return f"⏰ [{blue}{blue_bar}{red}{red_bar}{reset}] {remaining_time}"


def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def print_header():
    """Print the stylized header with sparkles."""
    cyan = '\033[96m'
    blue = '\033[94m'
    reset = '\033[0m'
    
    # Sparkle pattern
    sparkles = f"{cyan}✦ ✧ ✦ ✧ {reset}"
    
    print(f"{sparkles}{cyan}CLAUDE TOKEN MONITOR{reset} {sparkles}")
    print(f"{blue}{'=' * 60}{reset}")
    print()


def get_session_totals():
    """Get total tokens from ccusage session --json."""
    try:
        if is_running_in_wsl():
            # Running in WSL - use ccusage directly
            result = subprocess.run(
                ['ccusage', 'session', '--json'],
                capture_output=True,
                text=True,
                timeout=15
            )
        else:
            # Running in Windows - use WSL
            result = subprocess.run(
                ['wsl', 'bash', '-c', 'ccusage session --json'],
                capture_output=True,
                text=True,
                timeout=15
            )
        
        if result.returncode != 0:
            return None
            
        data = json.loads(result.stdout)
        if 'totals' in data and 'totalTokens' in data['totals']:
            return data['totals']['totalTokens']
        return None
        
    except Exception:
        return None

def load_session_state():
    """Load session state from JSON file."""
    try:
        with open('session_state.json', 'r') as f:
            data = json.load(f)
            # Convert ISO string back to datetime
            if 'session_start_time' in data:
                data['session_start_time'] = datetime.fromisoformat(data['session_start_time'])
            return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {}

def save_session_state(session_start_time, last_updated=None):
    """Save session state to JSON file."""
    if last_updated is None:
        last_updated = datetime.now(timezone.utc)
    
    data = {
        'session_start_time': session_start_time.isoformat(),
        'last_updated': last_updated.isoformat()
    }
    
    with open('session_state.json', 'w') as f:
        json.dump(data, f, indent=2)

def calculate_session_total_tokens(blocks, current_total_tokens):
    """Calculate total tokens within the current session timeframe."""
    # Load saved session state
    session_state = load_session_state()
    
    if 'session_start_time' in session_state and 'session_start_tokens' in session_state:
        # Use saved session start tokens
        session_start_tokens = session_state['session_start_tokens']
        session_tokens = current_total_tokens - session_start_tokens
        return max(0, session_tokens)
    
    # Fallback: calculate from blocks
    if not blocks:
        return 0
    
    total_tokens = 0
    for block in blocks:
        if not block.get('isGap', False):
            total_tokens += block.get('totalTokens', 0)
    
    # Initialize session_start_tokens if not set
    if current_total_tokens is not None:
        session_start_tokens = current_total_tokens - total_tokens
        session_state['session_start_tokens'] = session_start_tokens
        save_session_state(session_state.get('session_start_time', datetime.now(timezone.utc)))
    
    return total_tokens

def get_session_based_reset_time():
    """Calculate reset time based on persistent session state."""
    session_state = load_session_state()
    
    if 'session_start_time' in session_state:
        session_start = session_state['session_start_time']
        reset_time = session_start + timedelta(hours=5)
        return round_to_next_full_hour(reset_time)
    
    # Fallback to current time + 5 hours
    current_time = datetime.now(timezone.utc)
    reset_time = current_time + timedelta(hours=5)
    return round_to_next_full_hour(reset_time)

def round_to_next_full_hour(dt):
    """Round datetime to the next full hour."""
    if dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt
    else:
        return dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

def get_last_message_time(blocks):
    """Get the timestamp of the most recent message from blocks."""
    if not blocks:
        return None
    
    latest_time = None
    for block in blocks:
        if block.get('isGap', False):
            continue
            
        start_time_str = block.get('startTime')
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if latest_time is None or start_time > latest_time:
                    latest_time = start_time
            except ValueError:
                continue
    
    return latest_time

def format_time_remaining(seconds):
    """Format seconds into a human-readable time string."""
    if seconds <= 0:
        return "0m"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def main():
    """Main monitoring loop."""
    parser = argparse.ArgumentParser(description='Fixed Claude Token Monitor')
    parser.add_argument('--plan', choices=['pro', 'custom_max'], default='pro',
                       help='Token plan (pro=7000, custom_max=6500000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Set token limits
    if args.plan == 'pro':
        token_limit = 7000
    else:  # custom_max
        token_limit = 6500000
    
    # Colors for terminal output
    red = '\033[91m'
    green = '\033[92m'
    yellow = '\033[93m'
    blue = '\033[94m'
    cyan = '\033[96m'
    white = '\033[97m'
    gray = '\033[90m'
    reset = '\033[0m'
    
    # Check environment and ccusage availability
    env_info = "WSL" if is_running_in_wsl() else "Windows"
    if not check_ccusage_availability():
        print(f"❌ ccusage not available in {env_info}")
        if is_running_in_wsl():
            print("Please install ccusage in WSL: npm install -g @anthropic-ai/ccusage")
        else:
            print("Please install WSL and ccusage")
        return 1
    
    print(f"✅ Running in {env_info} with ccusage available")
    
    # Hide cursor
    print('\033[?25l', end='', flush=True)
    
    try:
        local_tz = pytz.timezone('Europe/Berlin')  # Adjust as needed
        
        while True:
            # Move cursor to top without clearing screen
            print('\033[H', end='', flush=True)
            
            current_time = datetime.now(timezone.utc)
            
            # Get ccusage data
            data = run_ccusage()
            blocks = data.get('blocks', []) if data else []
            
            # Get current total tokens
            current_total_tokens = get_session_totals()
            
            # Calculate session tokens (recalculate after potential session reset)
            session_reset_occurred = False
            if current_total_tokens is not None:
                tokens_used = calculate_session_total_tokens(blocks, current_total_tokens)
            else:
                # Fallback calculation from blocks only
                tokens_used = sum(block.get('totalTokens', 0) for block in blocks if not block.get('isGap', False))
            
            # Calculate reset time
            reset_time = get_session_based_reset_time()
            is_ready_for_new_session = current_time >= reset_time
            
            # Auto-start new session if current session has expired
            if is_ready_for_new_session:
                # Check if we have new activity (new blocks)
                if blocks and get_last_message_time(blocks):
                    last_activity = get_last_message_time(blocks)
                    # If there's recent activity (within last 10 minutes), start new session
                    if (current_time - last_activity).total_seconds() < 600:  # 10 minutes
                        # Start new session
                        new_session_start = current_time
                        # Calculate tokens used in current session before reset
                        current_session_tokens = tokens_used
                        
                        # Set new session start tokens: current total minus tokens used in this session
                        if current_total_tokens is not None:
                            new_session_start_tokens = current_total_tokens - current_session_tokens
                        else:
                            new_session_start_tokens = sum(block.get('totalTokens', 0) for block in blocks if not block.get('isGap', False)) - current_session_tokens
                        
                        # Save new session state
                        session_state = {
                            'session_start_time': new_session_start,
                            'session_start_tokens': new_session_start_tokens
                        }
                        save_session_state(new_session_start)
                        with open('session_state.json', 'w') as f:
                            data = {
                                'session_start_time': new_session_start.isoformat(),
                                'session_start_tokens': new_session_start_tokens,
                                'last_updated': current_time.isoformat()
                            }
                            json.dump(data, f, indent=2)
                        
                        # Recalculate with new session
                        reset_time = get_session_based_reset_time()
                        is_ready_for_new_session = False
                        session_reset_occurred = True
                        
                        # Calculate tokens used since new session start
                        if current_total_tokens is not None:
                            tokens_used = max(0, current_total_tokens - new_session_start_tokens)
                        else:
                            tokens_used = 0
            
            # Calculate remaining tokens and time
            tokens_remaining = max(0, token_limit - tokens_used)
            
            # Display header
            print_header()
            
            # Token usage with progress bar
            usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            
            if tokens_used > token_limit:
                status_icon = "🚨"
            elif tokens_used > token_limit * 0.9:
                status_icon = "⚠️"
            elif tokens_used > token_limit * 0.7:
                status_icon = "🟡"
            else:
                status_icon = "🎯"
            
            print(f"{status_icon} {white}Token Usage:{reset}    {create_token_progress_bar(usage_percentage)}")
            print(f"🎯 {white}Tokens Left:{reset}    {tokens_used:,} / {token_limit:,} (available: {tokens_remaining:,})")
            
            # Time to Reset section with progress bar
            if reset_time:
                time_to_reset = reset_time - current_time
                minutes_to_reset = time_to_reset.total_seconds() / 60
                
                # Get actual session start time for accurate progress calculation
                session_state = load_session_state()
                if session_state and 'session_start_time' in session_state:
                    session_start = session_state['session_start_time']
                    # Calculate actual elapsed time since session start
                    elapsed_time = current_time - session_start
                    elapsed_minutes = elapsed_time.total_seconds() / 60
                    # Calculate total session duration from start to reset
                    total_session_duration = (reset_time - session_start).total_seconds() / 60
                else:
                    # Fallback: use 5 hours as default
                    session_duration = 300  # 5 hours in minutes
                    elapsed_minutes = max(0, session_duration - minutes_to_reset)
                    total_session_duration = session_duration
                
                reset_local = reset_time.astimezone(local_tz)
                reset_str = reset_local.strftime("%H:%M")
                
                print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(elapsed_minutes, total_session_duration)}")
                print(f"🔄 {white}Session Reset:{reset} {reset_str}")
            else:
                # Ready for new session
                print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(0, 300)} {cyan}Ready for new session!{reset}")
                print(f"🔄 {white}Session Reset:{reset} Available now")
            
            # Last activity
            last_message_time = get_last_message_time(blocks)
            if last_message_time:
                last_message_local = last_message_time.astimezone(local_tz)
                last_message_str = last_message_local.strftime("%H:%M")
                time_since_last = current_time - last_message_time
                minutes_since_last = time_since_last.total_seconds() / 60
                
                if minutes_since_last < 1:
                    activity_status = f"{green}active now{reset}"
                elif minutes_since_last < 60:
                    activity_status = f"{yellow}{int(minutes_since_last)}m ago{reset}"
                else:
                    hours_since = int(minutes_since_last // 60)
                    mins_since = int(minutes_since_last % 60)
                    if mins_since == 0:
                        activity_status = f"{red}{hours_since}h ago{reset}"
                    else:
                        activity_status = f"{red}{hours_since}h {mins_since}m ago{reset}"
                
                print(f"💬 {white}Last Activity:{reset}  {last_message_str} ({activity_status})")
            
            print()
            
            # Debug information
            if args.debug:
                print(f"🔍 {white}Debug Information:{reset}")
                print(f"   🌍 Environment: {env_info}")
                print(f"   📊 Current total tokens: {current_total_tokens:,}" if current_total_tokens else "   📊 Current total tokens: N/A")
                print(f"   🎯 Session tokens: {int(tokens_used):,}")
                print(f"   📈 Active blocks: {len([b for b in blocks if not b.get('isGap', False)])}")
                print()
            
            # Notifications
            if tokens_used > token_limit:
                print(f"🚨 {red}TOKENS EXCEEDED MAX LIMIT! ({tokens_used:,} > {token_limit:,}){reset}")
                print()
            
            if is_ready_for_new_session and tokens_used > 0:
                print(f"✅ {green}Session window expired - ready for new 5-hour window!{reset}")
                print()
            
            # Status line
            current_time_str = datetime.now().strftime("%H:%M:%S")
            if is_ready_for_new_session:
                status_msg = f"{cyan}Waiting for new session...{reset}"
            else:
                status_msg = f"{cyan}Monitoring session...{reset}"
            
            debug_indicator = f" | {gray}Debug: ON{reset}" if args.debug else ""
            print(f"⏰ {gray}{current_time_str}{reset} 📝 {status_msg}{debug_indicator} | {gray}Ctrl+C to exit{reset} 🟨")
            
            # Clear any remaining lines
            print('\033[J', end='', flush=True)
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        # Show cursor before exiting
        print('\033[?25h', end='', flush=True)
        print(f"\n\n{cyan}Fixed monitoring stopped.{reset}")
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        sys.exit(0)
    except Exception:
        # Show cursor on any error
        print('\033[?25h', end='', flush=True)
        raise

if __name__ == "__main__":
    main()