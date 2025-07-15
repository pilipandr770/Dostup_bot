#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Create a lock file to ensure only one instance runs
LOCK_FILE="/tmp/dostup_bot.lock"
BOT_ALREADY_RUNNING=false

# Check if the lock file exists and process is still running
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null; then
        echo "Bot is already running with PID $PID"
        BOT_ALREADY_RUNNING=true
    else
        echo "Found stale lock file. Previous process $PID is not running."
    fi
fi

# Terminate ANY existing bot processes to prevent conflicts (more aggressive approach)
echo "Checking for existing bot processes..."
if ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep > /dev/null; then
  echo "Found existing bot processes:"
  ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep
  echo "Terminating existing bot processes..."
  pkill -f "python.*bot\.py" || echo "No bot.py processes to kill"
  pkill -f "python.*start\.py" || echo "No start.py processes to kill"
  sleep 2
  
  # Double-check that processes are actually terminated
  if ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep > /dev/null; then
    echo "WARNING: Failed to terminate all bot processes. Sending SIGKILL..."
    pkill -9 -f "python.*bot\.py" || echo "No bot.py processes to force kill"
    pkill -9 -f "python.*start\.py" || echo "No start.py processes to force kill"
    sleep 1
  fi
else
  echo "No existing bot processes found"
fi

# Write current PID to lock file
echo $$ > "$LOCK_FILE"
echo "Created lock file with PID $$"

# Wait a moment for processes to terminate
sleep 2

# Check if we're running in Docker
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container"
fi

# Set up trap to remove lock file when script exits
trap 'rm -f $LOCK_FILE; echo "Removed lock file on exit."' EXIT INT TERM

# Execute the start script - Explicitly use ONLY this command to start the bot
echo "Starting the bot via start.py..."
cd /app
exec python start.py
