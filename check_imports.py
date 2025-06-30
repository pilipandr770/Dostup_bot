#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("check_imports")

# Show Python path
logger.info("Python path:")
for path in sys.path:
    logger.info(f"  - {path}")

# Try to import the reminder_system module
try:
    import reminder_system
    logger.info("Successfully imported reminder_system")
except ImportError as e:
    logger.error(f"Failed to import reminder_system: {e}")

# Check if the reminder_system.py file exists in various locations
paths_to_check = [
    "/app/reminder_system.py",
    "/usr/local/lib/python3.11/site-packages/reminder_system.py",
    "/usr/local/lib/python3.11/site-packages/app/reminder_system.py"
]

for path in paths_to_check:
    if os.path.exists(path):
        logger.info(f"File exists: {path}")
    else:
        logger.warning(f"File not found: {path}")

print("Check complete. See logs for details.")
