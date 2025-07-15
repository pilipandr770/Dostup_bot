#!/bin/bash
set -e

# Print Python version for debugging
echo "Python version:"
python --version

# Explicitly install wheel and aiohttp with binary packages
echo "Installing aiohttp from binary packages..."
pip install wheel
pip install --only-binary :all: aiohttp==3.8.5

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# If reminder_system.py exists in app/, copy it to the root directory
if [ -f "app/reminder_system.py" ]; then
  echo "Copying reminder_system.py to the root directory"
  cp app/reminder_system.py ./
fi

echo "Build script completed successfully!"
