# This file will be copied to the same directory as the app/bot.py file
# It contains the ReminderSystem class from reminder_system.py to fix import issues

"""
Reminder System for Dostup Bot

This module handles tracking users who viewed free lessons and sending
reminder messages at configured intervals to encourage course purchases.
"""
import asyncio
import datetime
import logging
import os
import sqlite3
import time
from typing import Dict, List, Optional, Tuple, Any

from aiogram import Bot
import openai

# Setup logging
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_REMINDER_INTERVALS = [
    {"days": 1, "template": "Привет! Как тебе бесплатный урок? Готов ли ты углубиться в тему и получить полный доступ к курсу?"},
    {"days": 3, "template": "Здравствуй! Прошло несколько дней с того момента, как ты посмотрел наш бесплатный урок. Не хочешь получить доступ к полному курсу, чтобы узнать все секреты?"},
    {"days": 7, "template": "Привет! Уже неделя прошла с момента просмотра бесплатного урока. Самое время присоединиться к нашему сообществу и получить полный доступ к курсу!"}
]

class ReminderSystem:
    """Handles tracking free lesson views and sending scheduled reminders to users"""
    
    def __init__(self, bot: Bot, db_path: str = "reminder_data.db", 
                 reminder_intervals: List[Dict[str, Any]] = None,
                 openai_client = None, openai_assistant_id: str = None):
        """
        Initialize the reminder system
        
        Args:
            bot: Aiogram Bot instance for sending messages
            db_path: Path to the SQLite database file
            reminder_intervals: List of dicts with 'days' and 'template' keys
            openai_client: Optional OpenAI client for AI-generated reminders
            openai_assistant_id: Optional OpenAI Assistant ID
        """
        self.bot = bot
        self.db_path = db_path
        self.reminder_intervals = reminder_intervals or DEFAULT_REMINDER_INTERVALS
        self.openai_client = openai_client
        self.openai_assistant_id = openai_assistant_id
        self.is_running = False
        self.task = None
        
        # Initialize the database
        self._init_db()
        
    # Add the rest of your ReminderSystem class here as needed
    # This is just a placeholder to fix the import error
    
    def _init_db(self):
        """Initialize the SQLite database with necessary tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS viewed_lessons (
                    user_id INTEGER,
                    lesson_id TEXT,
                    view_date TIMESTAMP,
                    PRIMARY KEY (user_id, lesson_id)
                )
                ''')
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sent_reminders (
                    user_id INTEGER,
                    reminder_day INTEGER,
                    sent_date TIMESTAMP,
                    PRIMARY KEY (user_id, reminder_day)
                )
                ''')
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS purchased_users (
                    user_id INTEGER PRIMARY KEY,
                    purchase_date TIMESTAMP
                )
                ''')
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def track_lesson_view(self, user_id: int, lesson_id: str):
        """Record that a user viewed a free lesson"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO viewed_lessons VALUES (?, ?, ?)",
                    (user_id, lesson_id, datetime.datetime.now().isoformat())
                )
                conn.commit()
                logger.info(f"Recorded lesson view: User {user_id}, Lesson {lesson_id}")
                return True
        except Exception as e:
            logger.error(f"Error recording lesson view: {e}")
            return False

    def mark_as_purchased(self, user_id: int):
        """Mark a user as having purchased the course"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO purchased_users VALUES (?, ?)",
                    (user_id, datetime.datetime.now().isoformat())
                )
                conn.commit()
                logger.info(f"Marked user {user_id} as purchased")
                return True
        except Exception as e:
            logger.error(f"Error marking user as purchased: {e}")
            return False
    
    def start_reminder_service(self):
        """Start the background service to send reminders"""
        if self.is_running:
            logger.warning("Reminder service is already running")
            return False
        
        async def reminder_loop():
            while self.is_running:
                try:
                    await self.send_due_reminders()
                except Exception as e:
                    logger.error(f"Error in reminder loop: {e}")
                
                # Wait for 1 hour before checking again
                await asyncio.sleep(3600)
        
        self.is_running = True
        self.task = asyncio.create_task(reminder_loop())
        logger.info("Started reminder service")
        return True
    
    def stop_reminder_service(self):
        """Stop the background reminder service"""
        if not self.is_running:
            logger.warning("Reminder service is not running")
            return False
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        
        logger.info("Stopped reminder service")
        return True
    
    async def send_due_reminders(self):
        """Check and send all due reminders to users"""
        logger.info("Checking for due reminders...")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get users who viewed lessons but haven't purchased
                cursor.execute("""
                    SELECT DISTINCT v.user_id, v.view_date 
                    FROM viewed_lessons v
                    LEFT JOIN purchased_users p ON v.user_id = p.user_id
                    WHERE p.user_id IS NULL
                """)
                
                users = cursor.fetchall()
                logger.info(f"Found {len(users)} users who viewed lessons but haven't purchased")
                
                for user_id, view_date in users:
                    # Convert string date to datetime
                    if isinstance(view_date, str):
                        view_date = datetime.datetime.fromisoformat(view_date)
                    
                    now = datetime.datetime.now()
                    days_since_view = (now - view_date).days
                    
                    # Check each reminder interval
                    for reminder in self.reminder_intervals:
                        reminder_day = reminder["days"]
                        
                        # If we've reached this interval
                        if days_since_view >= reminder_day:
                            # Check if we already sent this reminder
                            cursor.execute(
                                "SELECT 1 FROM sent_reminders WHERE user_id = ? AND reminder_day = ?",
                                (user_id, reminder_day)
                            )
                            
                            if not cursor.fetchone():
                                # We haven't sent this reminder yet, send it
                                template = reminder["template"]
                                await self.send_reminder(user_id, template, reminder_day)
                                
                                # Record that we sent this reminder
                                cursor.execute(
                                    "INSERT INTO sent_reminders VALUES (?, ?, ?)",
                                    (user_id, reminder_day, now.isoformat())
                                )
                                conn.commit()
        except Exception as e:
            logger.error(f"Error checking due reminders: {e}")
    
    async def send_reminder(self, user_id: int, template: str, reminder_day: int):
        """Send a reminder message to a user"""
        try:
            # Use OpenAI to generate a personalized message if available
            message = template
            if self.openai_client and self.openai_assistant_id:
                try:
                    message = await self.generate_ai_reminder(template, reminder_day)
                except Exception as e:
                    logger.error(f"Error generating AI reminder: {e}")
            
            # Send the message
            await self.bot.send_message(user_id, message)
            logger.info(f"Sent day-{reminder_day} reminder to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    async def generate_ai_reminder(self, template: str, days_since_view: int):
        """Generate a personalized reminder message using OpenAI"""
        try:
            prompt = f"""
            Generate a personalized reminder message for a user who viewed our free lesson {days_since_view} days ago.
            The message should encourage them to purchase the full course.
            Base message: {template}
            Make it friendly, conversational, and not too salesy. Don't make it much longer than the base message.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant creating personalized reminder messages."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            
            message = response.choices[0].message.content.strip()
            logger.info(f"Generated AI reminder message for day {days_since_view}")
            return message
        except Exception as e:
            logger.error(f"Error generating AI reminder: {e}")
            return template  # Fall back to template if AI generation fails
    
    def get_stats(self):
        """Get statistics about the reminder system"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total number of users who viewed lessons
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM viewed_lessons")
                total_viewers = cursor.fetchone()[0] or 0
                
                # Get total number of users who purchased
                cursor.execute("SELECT COUNT(*) FROM purchased_users")
                total_purchases = cursor.fetchone()[0] or 0
                
                # Get conversion rate
                conversion_rate = 0
                if total_viewers > 0:
                    conversion_rate = (total_purchases / total_viewers) * 100
                
                # Get number of reminders sent
                cursor.execute("SELECT COUNT(*) FROM sent_reminders")
                total_reminders = cursor.fetchone()[0] or 0
                
                # Get reminders by day
                cursor.execute("""
                    SELECT reminder_day, COUNT(*) 
                    FROM sent_reminders 
                    GROUP BY reminder_day 
                    ORDER BY reminder_day
                """)
                reminders_by_day = dict(cursor.fetchall())
                
                return {
                    "total_viewers": total_viewers,
                    "total_purchases": total_purchases,
                    "conversion_rate": conversion_rate,
                    "total_reminders": total_reminders,
                    "reminders_by_day": reminders_by_day,
                    "is_running": self.is_running
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "error": str(e),
                "is_running": self.is_running
            }
