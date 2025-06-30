#!/usr/bin/env python3
import sys
import os

print("=== Python Import Debugging Tool ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print("\n=== PYTHONPATH ===")
print(os.environ.get('PYTHONPATH', 'Not set'))

print("\n=== sys.path ===")
for path in sys.path:
    print(f"- {path}")

print("\n=== Current directory contents ===")
print(f"Current working directory: {os.getcwd()}")
files = os.listdir('.')
for file in sorted(files):
    print(f"- {file}")

print("\n=== Parent directory contents ===")
try:
    parent_files = os.listdir('..')
    for file in sorted(parent_files):
        print(f"- {file}")
except Exception as e:
    print(f"Error listing parent directory: {e}")

print("\n=== Python modules ===")
try:
    import reminder_system
    print("✓ reminder_system module imported successfully")
    print(f"  Module location: {reminder_system.__file__}")
except ImportError as e:
    print(f"✗ Failed to import reminder_system: {e}")

try:
    from app.reminder_system import ReminderSystem
    print("✓ from app.reminder_system import ReminderSystem succeeded")
except ImportError as e:
    print(f"✗ Failed to import from app.reminder_system: {e}")

# Check specific paths
paths_to_check = [
    '/app/reminder_system.py',
    '/usr/local/lib/python3.11/site-packages/reminder_system.py',
    '/usr/local/lib/python3.11/site-packages/app/reminder_system.py'
]

print("\n=== Checking specific paths ===")
for path in paths_to_check:
    print(f"Path {path}: {'Exists' if os.path.exists(path) else 'Does not exist'}")

print("\n=== Debug Complete ===")
