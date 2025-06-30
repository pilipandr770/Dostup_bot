#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Check if we're running in Docker
if [ -f "/.dockerenv" ]; then
  echo "Running in Docker container"
  # Docker-specific logic here if needed
fi

# Execute the start script
echo "Starting the bot..."
exec python start.py
