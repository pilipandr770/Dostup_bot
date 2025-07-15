#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Create multiple lock files for extra security
MAIN_LOCK_FILE="/tmp/dostup_bot.lock"
RENDER_LOCK_FILE="/tmp/dostup_bot_render.lock"
SYSTEM_LOCK_FILE="/var/tmp/dostup_bot.lock"
BOT_ALREADY_RUNNING=false

# Function to terminate ALL existing bot processes (extra aggressive)
kill_all_bot_processes() {
    echo "Terminating ALL existing bot processes..."
    # Find all python processes related to the bot
    BOT_PIDS=$(ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep | awk '{print $2}')
    
    if [ -n "$BOT_PIDS" ]; then
        echo "Found bot processes with PIDs: $BOT_PIDS"
        for PID in $BOT_PIDS; do
            echo "Killing process $PID"
            kill -9 $PID 2>/dev/null || echo "Failed to kill $PID"
        done
    else
        echo "No bot processes found to kill"
    fi
    
    # Wait to ensure processes are terminated
    sleep 2
}

# Check for any existing lock files and running processes
if [ -f "$MAIN_LOCK_FILE" ] || [ -f "$RENDER_LOCK_FILE" ] || [ -f "$SYSTEM_LOCK_FILE" ]; then
    echo "Found existing lock file(s)"
    
    # Check MAIN_LOCK_FILE
    if [ -f "$MAIN_LOCK_FILE" ]; then
        PID=$(cat "$MAIN_LOCK_FILE")
        if ps -p "$PID" > /dev/null; then
            echo "Bot is already running with PID $PID (from main lock)"
            kill_all_bot_processes
        else
            echo "Found stale main lock file. Previous process $PID is not running."
        fi
    fi
    
    # Clean up any lock files
    rm -f "$MAIN_LOCK_FILE" "$RENDER_LOCK_FILE" "$SYSTEM_LOCK_FILE"
    echo "Removed all lock files for clean start"
fi

# Use the function to kill all bot processes regardless
kill_all_bot_processes

# Create lock files with our PID
echo $$ > "$MAIN_LOCK_FILE"
echo $$ > "$RENDER_LOCK_FILE"
[ -d "/var/tmp" ] && echo $$ > "$SYSTEM_LOCK_FILE"
echo "Created lock files with PID $$"

# Additional protection - write process info to a marker file
BOT_INFO_FILE="/tmp/dostup_bot_info.txt"
echo "Started at: $(date)" > "$BOT_INFO_FILE"
echo "PID: $$" >> "$BOT_INFO_FILE"
echo "Hostname: $(hostname)" >> "$BOT_INFO_FILE"

# Wait to ensure all processes have been terminated
sleep 3

# Check if we're running in Docker
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container"
fi

# Set up trap to remove lock files when script exits
trap 'rm -f $MAIN_LOCK_FILE $RENDER_LOCK_FILE $SYSTEM_LOCK_FILE $BOT_INFO_FILE; echo "Removed all lock files on exit."' EXIT INT TERM HUP

# Pass a unique startup ID to the bot to track instances
STARTUP_ID=$(date +%s%N)
export BOT_STARTUP_ID=$STARTUP_ID
echo "Bot startup ID: $STARTUP_ID" >> "$BOT_INFO_FILE"

# Execute the start script - Explicitly use ONLY this command to start the bot
echo "Starting the bot via start.py with startup ID $STARTUP_ID..."
cd /app
exec python start.py
