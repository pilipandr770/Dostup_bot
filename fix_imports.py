#!/usr/bin/env python3
import os
import sys
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_imports")

def main():
    """Fix imports in bot.py to allow running in both local and Cloud Run environments"""
    logger.info("Starting import fix")
    
    # Determine the bot.py file location
    bot_file = os.path.join('app', 'bot.py')
    if not os.path.exists(bot_file):
        logger.error(f"Could not find {bot_file}")
        sys.exit(1)
    
    logger.info(f"Found bot.py at {os.path.abspath(bot_file)}")
    
    # Read the file content
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a backup
    backup_file = f"{bot_file}.backup"
    shutil.copy2(bot_file, backup_file)
    logger.info(f"Created backup at {os.path.abspath(backup_file)}")
    
    # Modify the import statement
    if "from reminder_system import ReminderSystem" in content:
        logger.info("Found the import to modify")
        new_content = content.replace(
            "from reminder_system import ReminderSystem",
            """
# Try different import paths for reminder_system to handle both local and containerized environments
try:
    from reminder_system import ReminderSystem
except ImportError:
    try:
        from app.reminder_system import ReminderSystem
    except ImportError:
        # Add current directory to path and try again
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        try:
            from reminder_system import ReminderSystem
        except ImportError as e:
            logging.error(f"Failed to import ReminderSystem: {e}")
            # Create an empty placeholder class to prevent crashes
            class ReminderSystem:
                def __init__(self, bot, db_path=None, reminder_intervals=None, 
                            openai_client=None, openai_assistant_id=None):
                    logging.warning("Using placeholder ReminderSystem - reminders will not work!")
                    self.bot = bot
                    self.is_running = False
                def start(self):
                    logging.warning("Placeholder ReminderSystem.start() called")
                def stop(self):
                    logging.warning("Placeholder ReminderSystem.stop() called")
                def track_free_lesson_view(self, user_id):
                    logging.warning(f"Placeholder track_free_lesson_view called for user {user_id}")
                def get_stats(self):
                    return {"error": "ReminderSystem not available"}
            logging.warning("Created placeholder ReminderSystem class to prevent crashes")"""
        )
        
        # Write the modified content
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info("Successfully updated bot.py")
    else:
        logger.error("Could not find the import statement to replace")

if __name__ == "__main__":
    main()
