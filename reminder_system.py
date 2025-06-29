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
        self._init_db()
        
        logger.info(f"Reminder system initialized with {len(self.reminder_intervals)} intervals")
    
    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables"""
        try:
            # Ensure the directory for the database file exists
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            try:
                if not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                    logger.debug(f"Created directory for database: {db_dir}")
            except Exception as dir_error:
                logger.warning(f"Could not create database directory: {dir_error}")
            
            # Now connect and initialize tables
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Create table for tracking lesson views and reminders
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS lesson_views (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    view_time INTEGER,  -- Unix timestamp
                    has_purchased INTEGER DEFAULT 0,  -- Boolean flag
                    last_reminder_index INTEGER DEFAULT -1  -- Last reminder sent (-1 = none)
                )
                ''')
                
                # Create table for reminder history
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminder_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reminder_index INTEGER,
                    sent_time INTEGER,  -- Unix timestamp
                    was_ai_generated INTEGER DEFAULT 0,  -- Boolean flag
                    FOREIGN KEY (user_id) REFERENCES lesson_views(user_id)
                )
                ''')
                conn.commit()
                logger.debug(f"Database initialized successfully at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            logger.warning("Reminder system will operate in limited mode without database")
    
    async def track_lesson_view(self, user_id: int, username: str = None, 
                               first_name: str = None, last_name: str = None) -> None:
        """
        Record that a user has viewed the free lesson
        
        Args:
            user_id: Telegram user ID
            username: Optional Telegram username
            first_name: Optional user first name
            last_name: Optional user last name
        """
        logger.debug(f"Recording lesson view for user {user_id}")
        current_time = int(time.time())
        
        # Make sure we have a valid user_id
        if not user_id:
            logger.error("Cannot track lesson view: user_id is required")
            return
            
        try:
            # Verify database path exists
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.debug(f"Created directory for database: {db_dir}")
                except Exception as dir_error:
                    logger.error(f"Could not create database directory: {dir_error}")
                    return
                    
            # Connect to database and record view
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Check if user already exists
                cursor.execute(
                    "SELECT user_id FROM lesson_views WHERE user_id = ?", 
                    (user_id,)
                )
                if cursor.fetchone():
                    # Update existing record
                    cursor.execute(
                        """UPDATE lesson_views 
                           SET view_time = ?, username = ?, first_name = ?, last_name = ? 
                           WHERE user_id = ?""",
                        (current_time, username, first_name, last_name, user_id)
                    )
                    logger.debug(f"Updated existing record for user {user_id}")
                else:
                    # Create new record
                    cursor.execute(
                        """INSERT INTO lesson_views 
                           (user_id, username, first_name, last_name, view_time) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (user_id, username, first_name, last_name, current_time)
                    )
                    logger.debug(f"Created new record for user {user_id}")
                conn.commit()
                logger.info(f"Successfully recorded lesson view for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Database error tracking lesson view: {e}")
        except Exception as e:
            logger.error(f"Unexpected error tracking lesson view: {e}")
    
    async def mark_user_purchased(self, user_id: int) -> None:
        """
        Mark a user as having purchased the course
        
        Args:
            user_id: Telegram user ID
        """
        logger.debug(f"Marking user {user_id} as purchased")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE lesson_views SET has_purchased = 1 WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                logger.debug(f"User {user_id} marked as purchased")
        except sqlite3.Error as e:
            logger.error(f"Error marking purchase: {e}")
    
    async def _get_users_needing_reminders(self) -> List[Tuple[int, int, int]]:
        """
        Get list of users who need reminders
        
        Returns:
            List of tuples (user_id, last_reminder_index, view_time)
        """
        current_time = int(time.time())
        users_needing_reminders = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT user_id, last_reminder_index, view_time 
                       FROM lesson_views 
                       WHERE has_purchased = 0"""
                )
                for user_id, last_reminder_index, view_time in cursor.fetchall():
                    next_reminder_index = last_reminder_index + 1
                    if next_reminder_index >= len(self.reminder_intervals):
                        continue  # All reminders already sent
                    
                    # Calculate time since view
                    days_since_view = (current_time - view_time) / (60 * 60 * 24)
                    days_needed = self.reminder_intervals[next_reminder_index]["days"]
                    
                    if days_since_view >= days_needed:
                        users_needing_reminders.append((user_id, next_reminder_index, view_time))
                        logger.debug(f"User {user_id} needs reminder {next_reminder_index}")
        except sqlite3.Error as e:
            logger.error(f"Error getting users needing reminders: {e}")
        
        return users_needing_reminders
    
    async def _generate_ai_reminder(self, user_id: int, reminder_index: int) -> str:
        """
        Generate a personalized reminder message using OpenAI
        
        Args:
            user_id: Telegram user ID
            reminder_index: Index of the reminder (determines tone and urgency)
            
        Returns:
            AI-generated reminder message
        """
        if not self.openai_client or not self.openai_assistant_id:
            return self.reminder_intervals[reminder_index]["template"]
        
        try:
            logger.debug(f"Generating AI reminder for user {user_id}, index {reminder_index}")
            
            # Get user data
            user_info = {}
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username, first_name, last_name, view_time FROM lesson_views WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    username, first_name, last_name, view_time = result
                    user_info = {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "days_since_view": (int(time.time()) - view_time) / (60 * 60 * 24)
                    }
            
            # Create a thread
            thread = self.openai_client.beta.threads.create()
            
            # Add message to the thread
            prompt_text = f"""
            Сгенерируй напоминание для пользователя, который посмотрел бесплатный урок нашего курса,
            но еще не купил полный курс. Это {reminder_index + 1}-е напоминание.
            
            Информация о пользователе:
            Имя: {user_info.get("first_name", "Пользователь")}
            Прошло дней с просмотра урока: {user_info.get("days_since_view", "несколько")}
            
            Курс: "Успешный YouTube-бизнес с нуля"
            Цена: 149 евро
            
            Если это первое напоминание, сделай его мягким.
            Если это второе напоминание, добавь немного срочности.
            Если это третье или последующее напоминание, подчеркни, что это последний шанс.
            
            Сообщение должно быть коротким (до 200 символов), убедительным и побуждать к покупке.
            """
            
            self.openai_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt_text
            )
            
            # Run the Assistant
            run = self.openai_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.openai_assistant_id
            )
            
            # Wait for the run to complete (with timeout)
            max_wait_time = 30  # seconds
            start_time = time.time()
            while True:
                if time.time() - start_time > max_wait_time:
                    logger.warning(f"OpenAI request timed out for user {user_id}")
                    return self.reminder_intervals[reminder_index]["template"]
                
                run_status = self.openai_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    logger.warning(f"OpenAI run failed with status: {run_status.status}")
                    return self.reminder_intervals[reminder_index]["template"]
                
                await asyncio.sleep(1)
            
            # Get the assistant's response
            messages = self.openai_client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            for message in messages.data:
                if message.role == "assistant":
                    # Get the text content
                    for content_item in message.content:
                        if hasattr(content_item, "text"):
                            reminder_text = content_item.text.value
                            logger.debug(f"Generated AI reminder: {reminder_text[:50]}...")
                            return reminder_text
            
            # Fallback to template if no response
            return self.reminder_intervals[reminder_index]["template"]
            
        except Exception as e:
            logger.error(f"Error generating AI reminder: {e}")
            return self.reminder_intervals[reminder_index]["template"]
    
    async def _send_reminder(self, user_id: int, reminder_index: int, use_ai: bool = False) -> bool:
        """
        Send a reminder message to a user
        
        Args:
            user_id: Telegram user ID
            reminder_index: Index of the reminder to send
            use_ai: Whether to use AI to generate the message
            
        Returns:
            True if reminder was sent successfully
        """
        try:
            # Generate message text
            if use_ai and self.openai_client and self.openai_assistant_id:
                message_text = await self._generate_ai_reminder(user_id, reminder_index)
            else:
                message_text = self.reminder_intervals[reminder_index]["template"]
            
            # Add a call to action button
            message_text += "\n\n💳 Нажми кнопку 'Оплатить 149€' в меню, чтобы получить полный доступ к курсу!"
            
            # Send the message
            await self.bot.send_message(user_id, message_text)
            logger.info(f"Sent reminder {reminder_index} to user {user_id}")
            
            # Record that reminder was sent
            current_time = int(time.time())
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Update the last reminder index
                cursor.execute(
                    "UPDATE lesson_views SET last_reminder_index = ? WHERE user_id = ?",
                    (reminder_index, user_id)
                )
                # Record in history
                cursor.execute(
                    """INSERT INTO reminder_history 
                       (user_id, reminder_index, sent_time, was_ai_generated) 
                       VALUES (?, ?, ?, ?)""",
                    (user_id, reminder_index, current_time, 1 if use_ai else 0)
                )
                conn.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    async def process_reminders(self) -> None:
        """Process all pending reminders"""
        logger.debug("Processing reminders")
        users_needing_reminders = await self._get_users_needing_reminders()
        
        for user_id, reminder_index, _ in users_needing_reminders:
            use_ai = bool(self.openai_client and self.openai_assistant_id)
            await self._send_reminder(user_id, reminder_index, use_ai)
            
            # Add small delay to prevent flooding Telegram API
            await asyncio.sleep(0.5)
    
    async def _reminder_loop(self) -> None:
        """Main reminder processing loop"""
        logger.info("Starting reminder processing loop")
        self.is_running = True
        
        while self.is_running:
            try:
                await self.process_reminders()
                # Check every hour
                await asyncio.sleep(60 * 60)
            except asyncio.CancelledError:
                logger.info("Reminder loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in reminder loop: {e}")
                await asyncio.sleep(60)  # Sleep for a minute on error
    
    async def start(self) -> None:
        """Start the reminder system"""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._reminder_loop())
            logger.info("Reminder system started")
    
    async def stop(self) -> None:
        """Stop the reminder system"""
        if self.task and not self.task.done():
            self.is_running = False
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("Reminder system stopped")

# Helper function to get reminder system stats
async def get_reminder_stats(db_path: str = "reminder_data.db") -> Dict:
    """
    Get statistics about the reminder system
    
    Returns:
        Dict with stats
    """
    stats = {
        "total_users": 0,
        "users_with_reminders": 0,
        "reminders_sent": 0,
        "conversion_rate": 0.0,
    }
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM lesson_views")
            stats["total_users"] = cursor.fetchone()[0]
            
            # Users with reminders
            cursor.execute("SELECT COUNT(*) FROM lesson_views WHERE last_reminder_index >= 0")
            stats["users_with_reminders"] = cursor.fetchone()[0]
            
            # Total reminders sent
            cursor.execute("SELECT COUNT(*) FROM reminder_history")
            stats["reminders_sent"] = cursor.fetchone()[0]
            
            # Purchased users
            cursor.execute("SELECT COUNT(*) FROM lesson_views WHERE has_purchased = 1")
            purchased_users = cursor.fetchone()[0]
            
            # Calculate conversion rate
            if stats["total_users"] > 0:
                stats["conversion_rate"] = (purchased_users / stats["total_users"]) * 100
    except sqlite3.Error as e:
        logger.error(f"Error getting reminder stats: {e}")
    
    return stats
