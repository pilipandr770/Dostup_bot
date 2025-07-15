#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Terminate any existing bot processes to prevent conflicts
echo "Checking for existing bot processes..."
if ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep > /dev/null; then
  echo "Found existing bot processes:"
  ps aux | grep -E "python.*(bot\.py|start\.py)" | grep -v grep
  echo "Terminating existing bot processes..."
  pkill -f "python.*bot\.py" || echo "No bot.py processes to kill"
  pkill -f "python.*start\.py" || echo "No start.py processes to kill"
else
  echo "No existing bot processes found"
fi

# Wait a moment for processes to terminate
sleep 2

# Check if we're running in Docker
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container"
fi

# Execute the start script - Explicitly use ONLY this command to start the bot
echo "Starting the bot via start.py..."
cd /app
exec python start.py
