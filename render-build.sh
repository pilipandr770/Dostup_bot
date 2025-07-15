#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# If we're not running in Docker, ensure we install the correct aiohttp version
if [ -z "$DOCKER_CONTAINER" ]; then
  echo "Not running in Docker, installing packages directly..."
  
  # Try to use Python 3.11 if available
  if command -v python3.11 &>/dev/null; then
    echo "Using Python 3.11"
    python3.11 -m pip install wheel
    python3.11 -m pip install --only-binary :all: aiohttp==3.8.5
    python3.11 -m pip install -r requirements.txt
  else
    echo "Python 3.11 not found, using default Python"
    pip install wheel
    pip install --only-binary :all: aiohttp==3.8.5
    pip install -r requirements.txt
  fi
else
  echo "Running in Docker, packages should be installed via Dockerfile"
fi

echo "Build script completed"
