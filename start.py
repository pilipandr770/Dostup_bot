#!/usr/bin/env python3
import os
import sys
import logging
import platform

# Removed direct import of app.bot to handle it more safely below

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start")

# Log Python version
python_version = sys.version.replace('\n', ' ')
logger.info(f"Python version: {python_version}")
logger.info(f"Python implementation: {platform.python_implementation()}")
logger.info(f"System: {platform.system()} {platform.release()}")

# Add the necessary directories to Python path
logger.info("Setting up Python path")
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, 'app')

# Make sure reminder_system can be imported
logger.info(f"Current directory: {current_dir}")
logger.info(f"App directory: {app_dir}")

# Add all possible paths
sys.path.insert(0, app_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, '/app')
sys.path.insert(0, '/usr/local/lib/python3.11/site-packages')
sys.path.insert(0, '/usr/local/lib/python3.11/site-packages/app')

# Log the Python path for debugging
logger.info(f"Python path: {sys.path}")

# Check if the reminder_system.py file exists
possible_reminder_paths = [
    os.path.join(app_dir, 'reminder_system.py'),
    os.path.join('/app', 'reminder_system.py'),
    os.path.join('/usr/local/lib/python3.11/site-packages', 'reminder_system.py'),
    os.path.join('/usr/local/lib/python3.11/site-packages/app', 'reminder_system.py')
]

for path in possible_reminder_paths:
    if os.path.exists(path):
        logger.info(f"Found reminder_system.py at: {path}")
    else:
        logger.warning(f"reminder_system.py not found at: {path}")

# Detect if we're running in Cloud Run (PORT env variable is set)
is_cloud_run = "PORT" in os.environ
logger.info(f"Running in Cloud Run: {is_cloud_run}")

# Import cloud_run_adapter if we're running in Cloud Run
if is_cloud_run:
    try:
        logger.info("Trying to import cloud_run_adapter")
        from cloud_run_adapter import init_cloud_run_adapter
        logger.info("Successfully imported cloud_run_adapter")
    except ImportError as e:
        logger.error(f"Could not import cloud_run_adapter: {e}")
        sys.exit(1)

# Try to directly import reminder_system first to validate it's available
try:
    logger.info("Trying to import reminder_system directly")
    import reminder_system
    logger.info(f"Successfully imported reminder_system from: {reminder_system.__file__}")
except ImportError as e:
    logger.error(f"Could not import reminder_system: {e}")
    logger.error("This will cause bot.py to fail. Attempting to continue anyway...")

# Import the bot
try:
    logger.info("Trying to import app.bot")
    from app.bot import start_polling
    logger.info("Successfully imported app.bot")
except ImportError as e:
    logger.error(f"Could not import bot: {e}")
    # Try alternative import paths
    try:
        logger.info("Trying alternative import for bot")
        sys.path.insert(0, '.')
        from bot import start_polling
        logger.info("Successfully imported bot from current directory")
    except ImportError as e2:
        logger.error(f"All import attempts failed: {e2}")
        sys.exit(1)
except SyntaxError as e:
    logger.error(f"Syntax error in bot.py: {e}")
    sys.exit(1)
except IndentationError as e:
    logger.error(f"Indentation error in bot.py: {e}")
    sys.exit(1)

if __name__ == "__main__":
    logger.info("Main block starting")
    if is_cloud_run:
        # If we're running in Cloud Run, use the adapter
        logger.info("Starting bot with Cloud Run adapter")
        init_cloud_run_adapter(start_polling)
    else:
        # Otherwise, start the bot directly
        logger.info("Starting bot directly")
        start_polling()
