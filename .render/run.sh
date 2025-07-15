#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Terminate any existing bot processes
echo "Checking for existing bot processes..."
ps aux | grep "python.*bot.py" | grep -v grep
if pgrep -f "python.*bot.py" > /dev/null; then
  echo "Found existing bot process, terminating..."
  pkill -f "python.*bot.py" || echo "No processes to kill"
else
  echo "No existing bot processes found"
fi

# Check if we're running in Docker
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container"
  # Docker-specific logic here if needed
fi

# Execute the start script
echo "Starting the bot..."
exec python start.py
