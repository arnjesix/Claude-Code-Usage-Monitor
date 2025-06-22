#!/usr/bin/env python3

import subprocess
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz
import shutil


def check_ccusage_availability():
    """Check if ccusage command is available on the system."""
    return shutil.which('ccusage') is not None


def check_nodejs_availability():
    """Check if Node.js is available on the system."""
    return shutil.which('node') is not None or shutil.which('nodejs') is not None


def check_npm_availability():
    """Check if npm is available on the system."""
    return shutil.which('npm') is not None


def print_installation_instructions():
    """Print detailed installation instructions based on what's available."""
    print("❌ Error: 'ccusage' command not found!")
    print()
    print("🐧 This tool requires WSL (Windows Subsystem for Linux) on Windows.")
    print("📋 Installation steps:")
    print("   1. Open WSL terminal (wsl or Ubuntu app)")
    print("   2. Install Node.js in WSL: sudo apt update && sudo apt install nodejs npm")
    print("   3. Install ccusage: sudo npm install -g ccusage")
    print("   4. Run this script in WSL using Python")
    print()
    print("🚀 To run the monitor in WSL:")
    print("   1. cd /mnt/c/Users/arnje/Documents/VS-Code/Claude-Code/Claude-Code-Usage-Monitor")
    print("   2. source venv/bin/activate")
    print("   3. python ccusage_monitor.py")
    print()
    print("💡 Note: ccusage works best in Linux/WSL environment")
    print("📝 For more info: https://www.npmjs.com/package/ccusage")


def run_ccusage():
    """Execute ccusage blocks --json command and return parsed JSON data."""
    # First check if ccusage is available
    if not check_ccusage_availability():
        return None
    
    try:
        result = subprocess.run(['ccusage', 'blocks', '--json'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running ccusage command: {e}")
        print(f"📋 Command output: {e.stderr if e.stderr else 'No error output'}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON output from ccusage: {e}")
        return None
    except FileNotFoundError:
        print("❌ Error: 'ccusage' command not found!")
        print("📋 Please install ccusage by following these steps:")
        print("   1. Install Node.js from https://nodejs.org/")
        print("   2. Run: npm install -g @anthropic-ai/ccusage")
        print("   3. Restart your terminal and try again")
        return None


def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


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


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return '🐌'  # Slow
    elif burn_rate < 150:
        return '➡️'  # Normal
    elif burn_rate < 300:
        return '🚀'  # Fast
    else:
        return '⚡'  # Very fast


def calculate_hourly_burn_rate(blocks, current_time):
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0
    
    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = 0
    
    for block in blocks:
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        # Parse start time
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Skip gaps
        if block.get('isGap', False):
            continue
            
        # Determine session end time
        if block.get('isActive', False):
            # For active sessions, use current time
            session_actual_end = current_time
        else:
            # For completed sessions, use actualEndTime or current time
            actual_end_str = block.get('actualEndTime')
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
            else:
                session_actual_end = current_time
        
        # Check if session overlaps with the last hour
        if session_actual_end < one_hour_ago:
            # Session ended before the last hour
            continue
            
        # Calculate how much of this session falls within the last hour
        session_start_in_hour = max(start_time, one_hour_ago)
        session_end_in_hour = min(session_actual_end, current_time)
        
        if session_end_in_hour <= session_start_in_hour:
            continue
            
        # Calculate portion of tokens used in the last hour
        total_session_duration = (session_actual_end - start_time).total_seconds() / 60  # minutes
        hour_duration = (session_end_in_hour - session_start_in_hour).total_seconds() / 60  # minutes
        
        if total_session_duration > 0:
            session_tokens = block.get('totalTokens', 0)
            tokens_in_hour = session_tokens * (hour_duration / total_session_duration)
            total_tokens += tokens_in_hour
    
    # Return tokens per minute
    return total_tokens / 60 if total_tokens > 0 else 0


def get_session_state_file():
    """Get the path to the session state file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'session_state.json')


def load_session_state():
    """Load the saved session state from file."""
    state_file = get_session_state_file()
    if not os.path.exists(state_file):
        return None
    
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert ISO string back to datetime
            if 'session_start_time' in data:
                data['session_start_time'] = datetime.fromisoformat(data['session_start_time'])
            return data
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"Warning: Could not load session state: {e}")
        return None


def save_session_state(session_start_time):
    """Save the current session state to file."""
    state_file = get_session_state_file()
    
    data = {
        'session_start_time': session_start_time.isoformat(),
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save session state: {e}")


def get_last_session_info(blocks):
    """Find the most recent session (active or completed) and return its info."""
    if not blocks:
        return None, None
    
    latest_session = None
    latest_start_time = None
    
    for block in blocks:
        # Skip gaps
        if block.get('isGap', False):
            continue
            
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Check if this is the latest session
        if latest_start_time is None or start_time > latest_start_time:
            latest_session = block
            latest_start_time = start_time
    
    return latest_session, latest_start_time


def get_session_window_info(blocks, current_time):
    """Get info about the current 5-hour session window: first session and last session."""
    if not blocks:
        return None, None, None, None
    
    # Find the most recent session to determine the current window
    latest_session, latest_start_time = get_last_session_info(blocks)
    
    if not latest_session or not latest_start_time:
        return None, None, None, None
    
    # Calculate the 5-hour window based on the latest session
    window_start = latest_start_time
    window_end = latest_start_time + timedelta(hours=5)
    
    # If we're past the window and no active session, there's no current window
    has_active_session = any(block.get('isActive', False) for block in blocks if not block.get('isGap', False))
    if current_time > window_end and not has_active_session:
        return None, None, None, None
    
    # Find all sessions within this 5-hour window
    sessions_in_window = []
    for block in blocks:
        if block.get('isGap', False):
            continue
            
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Check if this session falls within the current window
        if window_start <= start_time <= window_end:
            sessions_in_window.append((block, start_time))
    
    if not sessions_in_window:
        return None, None, None, None
    
    # Sort by start time
    sessions_in_window.sort(key=lambda x: x[1])
    
    # First and last session in the window
    first_session, first_start_time = sessions_in_window[0]
    last_session, last_start_time = sessions_in_window[-1]
    
    return first_session, first_start_time, last_session, last_start_time


def get_session_based_reset_time(current_time, blocks):
    """Calculate reset time based on persistent session state + 5 hours.
    Uses saved session state to maintain consistency across monitor restarts.
    """
    # First, try to load the saved session state
    saved_state = load_session_state()
    
    if saved_state and 'session_start_time' in saved_state:
        saved_session_start = saved_state['session_start_time']
        saved_reset_time = saved_session_start + timedelta(hours=5)
        
        # Check if the saved session is still valid (not expired)
        if current_time < saved_reset_time:
            # Saved session is still valid, use it
            has_active_session = any(block.get('isActive', False) for block in blocks if not block.get('isGap', False))
            return saved_reset_time
        else:
            # Saved session has expired, check if there's a new session after expiry
            latest_session, latest_start_time = get_last_session_info(blocks)
            
            if latest_session and latest_start_time:
                # Check if there's a session that started after the saved session expired
                if latest_start_time > saved_reset_time:
                    # New session started after old session expired - save new session start
                    save_session_state(latest_start_time)
                    return latest_start_time + timedelta(hours=5)
                else:
                    # No new session after expiry - ready for new session
                    return None
            else:
                # No sessions found - ready for new session
                return None
    else:
        # No saved state, use current session logic
        latest_session, latest_start_time = get_last_session_info(blocks)
        
        if not latest_session or not latest_start_time:
            # No sessions found - ready for new session
            return None
        
        # Save this as the new session start
        save_session_state(latest_start_time)
        
        # Calculate when this session should reset (start time + 5 hours)
        session_reset_time = latest_start_time + timedelta(hours=5)
        
        # Check if there's currently an active session
        has_active_session = any(block.get('isActive', False) for block in blocks if not block.get('isGap', False))
        
        if has_active_session:
            # There's an active session, so use the calculated reset time
            return session_reset_time
        else:
            # No active session
            if current_time >= session_reset_time:
                # Last session expired and no new session started - ready for new session
                return None
            else:
                # Last session still within 5-hour window but not active
                return session_reset_time


def get_persistent_session_window_info(blocks, current_time):
    """Get session window info based on persistent session state."""
    # Load saved session state
    saved_state = load_session_state()
    
    if saved_state and 'session_start_time' in saved_state:
        saved_session_start = saved_state['session_start_time']
        saved_reset_time = saved_session_start + timedelta(hours=5)
        
        # Check if the saved session is still valid
        if current_time < saved_reset_time:
            # Use saved session as window start
            window_start = saved_session_start
            window_end = saved_reset_time
        else:
            # Saved session expired, check for new session
            latest_session, latest_start_time = get_last_session_info(blocks)
            if latest_session and latest_start_time and latest_start_time > saved_reset_time:
                # New session after expiry
                window_start = latest_start_time
                window_end = latest_start_time + timedelta(hours=5)
            else:
                # No valid window
                return None, None, None, None
    else:
        # No saved state, use current session
        latest_session, latest_start_time = get_last_session_info(blocks)
        if not latest_session or not latest_start_time:
            return None, None, None, None
        
        window_start = latest_start_time
        window_end = latest_start_time + timedelta(hours=5)
    
    # Find all sessions within this window
    sessions_in_window = []
    for block in blocks:
        if block.get('isGap', False):
            continue
            
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Check if this session falls within the current window
        if window_start <= start_time <= window_end:
            sessions_in_window.append((block, start_time))
    
    if not sessions_in_window:
        return None, None, None, None
    
    # Sort by start time
    sessions_in_window.sort(key=lambda x: x[1])
    
    # First and last session in the window
    first_session, first_start_time = sessions_in_window[0]
    last_session, last_start_time = sessions_in_window[-1]
    
    return first_session, first_start_time, last_session, last_start_time


def get_next_reset_time(current_time, custom_reset_hour=None, timezone_str='Europe/Warsaw'):
    """Calculate next token reset time based on fixed 5-hour intervals.
    Default reset times in specified timezone: 04:00, 09:00, 14:00, 18:00, 23:00
    Or use custom reset hour if provided.
    This function is kept for backward compatibility but not used in session-based mode.
    """
    # Convert to specified timezone
    try:
        target_tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Warning: Unknown timezone '{timezone_str}', using Europe/Warsaw")
        target_tz = pytz.timezone('Europe/Warsaw')
    
    # If current_time is timezone-aware, convert to target timezone
    if current_time.tzinfo is not None:
        target_time = current_time.astimezone(target_tz)
    else:
        # Assume current_time is in target timezone if not specified
        target_time = target_tz.localize(current_time)
    
    if custom_reset_hour is not None:
        # Use single daily reset at custom hour
        reset_hours = [custom_reset_hour]
    else:
        # Default 5-hour intervals
        reset_hours = [4, 9, 14, 18, 23]
    
    # Get current hour and minute
    current_hour = target_time.hour
    current_minute = target_time.minute
    
    # Find next reset hour
    next_reset_hour = None
    for hour in reset_hours:
        if current_hour < hour or (current_hour == hour and current_minute == 0):
            next_reset_hour = hour
            break
    
    # If no reset hour found today, use first one tomorrow
    if next_reset_hour is None:
        next_reset_hour = reset_hours[0]
        next_reset_date = target_time.date() + timedelta(days=1)
    else:
        next_reset_date = target_time.date()
    
    # Create next reset datetime in target timezone
    next_reset = target_tz.localize(
        datetime.combine(next_reset_date, datetime.min.time().replace(hour=next_reset_hour)),
        is_dst=None
    )
    
    # Convert back to the original timezone if needed
    if current_time.tzinfo is not None and current_time.tzinfo != target_tz:
        next_reset = next_reset.astimezone(current_time.tzinfo)
    
    return next_reset


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Claude Token Monitor - Real-time token usage monitoring')
    parser.add_argument('--plan', type=str, default='pro', 
                        choices=['pro', 'max5', 'max20', 'custom_max'],
                        help='Claude plan type (default: pro). Use "custom_max" to auto-detect from highest previous block')
    parser.add_argument('--reset-hour', type=int, 
                        help='Change the reset hour (0-23) for daily limits')
    parser.add_argument('--timezone', type=str, default='Europe/Warsaw',
                        help='Timezone for reset times (default: Europe/Warsaw). Examples: US/Eastern, Asia/Tokyo, UTC')
    return parser.parse_args()


def get_token_limit(plan, blocks=None):
    """Get token limit based on plan type."""
    if plan == 'custom_max' and blocks:
        # Find the highest token count from all previous blocks
        max_tokens = 0
        for block in blocks:
            if not block.get('isGap', False) and not block.get('isActive', False):
                tokens = block.get('totalTokens', 0)
                if tokens > max_tokens:
                    max_tokens = tokens
        # Return the highest found, or default to pro if none found
        return max_tokens if max_tokens > 0 else 7000
    
    limits = {
        'pro': 7000,
        'max5': 35000,
        'max20': 140000
    }
    return limits.get(plan, 7000)


def main():
    """Main monitoring loop."""
    args = parse_args()
    
    # Color codes defined early for use in error handling
    cyan = '\033[96m'
    green = '\033[92m'
    blue = '\033[94m'
    red = '\033[91m'
    yellow = '\033[93m'
    white = '\033[97m'
    gray = '\033[90m'
    reset = '\033[0m'
    
    # Check if ccusage is available before starting
    if not check_ccusage_availability():
        print_installation_instructions()
        print(f"\n{red}Exiting...{reset} Please install ccusage and try again.")
        sys.exit(1)
    
    # For 'custom_max' plan, we need to get data first to determine the limit
    if args.plan == 'custom_max':
        initial_data = run_ccusage()
        if initial_data and 'blocks' in initial_data:
            token_limit = get_token_limit(args.plan, initial_data['blocks'])
        else:
            token_limit = get_token_limit('pro')  # Fallback to pro
    else:
        token_limit = get_token_limit(args.plan)
    
    try:
        # Initial screen clear and hide cursor
        os.system('clear' if os.name == 'posix' else 'cls')
        print('\033[?25l', end='', flush=True)  # Hide cursor
        
        while True:
            # Move cursor to top without clearing
            print('\033[H', end='', flush=True)
            
            data = run_ccusage()
            if not data or 'blocks' not in data:
                print("❌ Failed to get usage data")
                print("🔄 Retrying in 3 seconds...")
                time.sleep(3)
                continue
            
            # Find the active block
            active_block = None
            for block in data['blocks']:
                if block.get('isActive', False):
                    active_block = block
                    break
            
            if not active_block:
                print("⚠️  No active session found")
                print("🔄 Retrying in 3 seconds...")
                time.sleep(3)
                continue
            
            # Extract data from active block
            tokens_used = active_block.get('totalTokens', 0)
            
            # Check if tokens exceed limit and switch to custom_max if needed
            if tokens_used > token_limit and args.plan == 'pro':
                # Auto-switch to custom_max when pro limit is exceeded
                new_limit = get_token_limit('custom_max', data['blocks'])
                if new_limit > token_limit:
                    token_limit = new_limit
            
            usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            tokens_left = token_limit - tokens_used
            
            # Time calculations
            start_time_str = active_block.get('startTime')
            current_time = datetime.now(timezone.utc)  # Initialize current_time with UTC timezone
            
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                current_time = datetime.now(start_time.tzinfo)
                elapsed = current_time - start_time
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
            
            session_duration = 300  # 5 hours in minutes
            remaining_minutes = max(0, session_duration - elapsed_minutes)
            
            # Calculate burn rate from ALL sessions in the last hour
            burn_rate = calculate_hourly_burn_rate(data['blocks'], current_time)
            
            # Session-based reset time calculation
            reset_time = get_session_based_reset_time(current_time, data['blocks'])
            
            # Get session window information using persistent state
            first_session, first_start_time, last_session, last_start_time = get_persistent_session_window_info(data['blocks'], current_time)
            
            if reset_time is None:
                # Ready for new session - show full 5-hour window available
                minutes_to_reset = 300  # Full 5 hours available
                time_since_reset = 0
                is_ready_for_new_session = True
            else:
                # Calculate time to reset
                time_to_reset = reset_time - current_time
                minutes_to_reset = time_to_reset.total_seconds() / 60
                
                # Calculate time since session started (for progress bar) - use persistent session start
                saved_state = load_session_state()
                if saved_state and 'session_start_time' in saved_state:
                    session_start_time = saved_state['session_start_time']
                    time_since_session_start = current_time - session_start_time
                    time_since_reset = time_since_session_start.total_seconds() / 60
                else:
                    # Fallback to latest session
                    latest_session, latest_start_time = get_last_session_info(data['blocks'])
                    if latest_start_time:
                        time_since_session_start = current_time - latest_start_time
                        time_since_reset = time_since_session_start.total_seconds() / 60
                    else:
                        time_since_reset = 0
                is_ready_for_new_session = False
            
            # Predicted end calculation - when tokens will run out based on burn rate
            if burn_rate > 0 and tokens_left > 0:
                minutes_to_depletion = tokens_left / burn_rate
                predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
            else:
                # If no burn rate or tokens already depleted, use reset time or current time
                if reset_time:
                    predicted_end_time = reset_time
                else:
                    predicted_end_time = current_time
            
            # Display header
            print_header()
            
            # Token Usage section
            print(f"📊 {white}Token Usage:{reset}    {create_token_progress_bar(usage_percentage)}")
            print()
            
            # Time to Reset section - calculate progress based on time since last session start
            if is_ready_for_new_session:
                print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(0, 300)} {cyan}Ready for new session!{reset}")
            else:
                print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(time_since_reset, 300)}")
            print()
            
            # Detailed stats
            print(f"🎯 {white}Tokens:{reset}         {white}{tokens_used:,}{reset} / {gray}~{token_limit:,}{reset} ({cyan}{tokens_left:,} left{reset})")
            print(f"🔥 {white}Burn Rate:{reset}      {yellow}{burn_rate:.1f}{reset} {gray}tokens/min{reset}")
            print()
            
            # Predictions - convert to configured timezone for display
            try:
                local_tz = pytz.timezone(args.timezone)
            except:
                local_tz = pytz.timezone('Europe/Warsaw')
            predicted_end_local = predicted_end_time.astimezone(local_tz)
            
            predicted_end_str = predicted_end_local.strftime("%H:%M")
            print(f"🏁 {white}Predicted End:{reset} {predicted_end_str}")
            
            if reset_time:
                reset_time_local = reset_time.astimezone(local_tz)
                reset_time_str = reset_time_local.strftime("%H:%M")
                print(f"🔄 {white}Session Reset:{reset} {reset_time_str}")
            else:
                print(f"🔄 {white}Session Reset:{reset} {cyan}Ready for new session{reset}")
            
            # Show session window info
            if first_start_time and last_start_time:
                first_start_local = first_start_time.astimezone(local_tz)
                last_start_local = last_start_time.astimezone(local_tz)
                first_start_str = first_start_local.strftime("%H:%M")
                last_start_str = last_start_local.strftime("%H:%M")
                
                if first_start_time == last_start_time:
                    # Only one session in the window
                    print(f"📝 {white}Session Start:{reset}  {first_start_str}")
                else:
                    # Multiple sessions in the window
                    print(f"📝 {white}First Message:{reset}  {first_start_str}")
                    print(f"📝 {white}Last Message:{reset}   {last_start_str}")
                
                # Show persistent session info
                saved_state = load_session_state()
                if saved_state and 'session_start_time' in saved_state:
                    persistent_start = saved_state['session_start_time'].astimezone(local_tz)
                    persistent_start_str = persistent_start.strftime("%d.%m.%Y %H:%M")
                    print(f"💾 {white}Saved Session:{reset}  {gray}{persistent_start_str}{reset}")
            elif is_ready_for_new_session:
                print(f"📝 {white}Session Info:{reset}    {gray}No active session window{reset}")
            
            print()
            
            # Show notification if we switched to custom_max
            show_switch_notification = False
            if tokens_used > 7000 and args.plan == 'pro' and token_limit > 7000:
                show_switch_notification = True
            
            # Notification when tokens exceed max limit
            show_exceed_notification = tokens_used > token_limit
            
            # Show notifications
            if show_switch_notification:
                print(f"🔄 {yellow}Tokens exceeded Pro limit - switched to custom_max ({token_limit:,}){reset}")
                print()
            
            if show_exceed_notification:
                print(f"🚨 {red}TOKENS EXCEEDED MAX LIMIT! ({tokens_used:,} > {token_limit:,}){reset}")
                print()
            
            # Warning if tokens will run out before reset
            if reset_time and predicted_end_time < reset_time:
                print(f"⚠️  {red}Tokens will run out BEFORE session reset!{reset}")
                print()
            elif is_ready_for_new_session and tokens_used > 0:
                print(f"✅ {green}Session window expired - ready for new 5-hour window!{reset}")
                print()
            
            # Status line
            current_time_str = datetime.now().strftime("%H:%M:%S")
            if is_ready_for_new_session:
                status_msg = f"{cyan}Waiting for new session...{reset}"
            else:
                status_msg = f"{cyan}Session active...{reset}"
            print(f"⏰ {gray}{current_time_str}{reset} 📝 {status_msg} | {gray}Ctrl+C to exit{reset} 🟨")
            
            # Clear any remaining lines below to prevent artifacts
            print('\033[J', end='', flush=True)
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        # Show cursor before exiting
        print('\033[?25h', end='', flush=True)
        print(f"\n\n{cyan}Monitoring stopped.{reset}")
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        sys.exit(0)
    except Exception:
        # Show cursor on any error
        print('\033[?25h', end='', flush=True)
        raise


if __name__ == "__main__":
    main()