#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis-based distributed locking mechanism for the Dostup bot.
This provides a more robust alternative to file-based locking when
multiple instances of the bot are running in a distributed environment.
"""

import os
import time
import uuid
import logging
import redis
import signal
import socket
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('redis_lock')

class RedisLock:
    """
    Distributed locking implementation using Redis.
    This ensures that only one bot instance can run at a time.
    """
    
    def __init__(self, redis_url=None, lock_name="dostup_bot_lock", ttl=60, retry_interval=1, max_retries=30):
        """
        Initialize Redis lock
        
        Args:
            redis_url: Redis connection URL (e.g. redis://localhost:6379/0)
            lock_name: Name of the lock key in Redis
            ttl: Time-to-live in seconds for the lock
            retry_interval: Seconds to wait between retry attempts
            max_retries: Maximum number of retries to acquire lock
        """
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.lock_name = lock_name
        self.ttl = ttl
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.lock_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"
        self.redis = None
        self.locked = False
        
        # Set up a heartbeat thread to keep the lock valid
        self._heartbeat_running = False
    
    def connect(self):
        """Establish connection to Redis"""
        if self.redis is None:
            try:
                self.redis = redis.from_url(self.redis_url)
                logger.info(f"Connected to Redis at {self.redis_url}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                return False
        return True
    
    def acquire(self):
        """
        Acquire the lock with retries.
        
        Returns:
            bool: True if lock was acquired, False otherwise
        """
        if not self.connect():
            logger.error("Cannot acquire lock - Redis connection failed")
            return False
        
        logger.info(f"Attempting to acquire lock '{self.lock_name}' with ID {self.lock_id}")
        
        # Try to acquire the lock with retries
        for attempt in range(self.max_retries):
            # Use Redis SET NX (not exists) with expiration
            acquired = self.redis.set(
                self.lock_name, 
                self.lock_id,
                nx=True,  # Only set if key doesn't exist
                ex=self.ttl  # Expiration time
            )
            
            if acquired:
                logger.info(f"Lock '{self.lock_name}' acquired successfully")
                self.locked = True
                
                # Start the heartbeat to keep the lock alive
                self._start_heartbeat()
                
                # Register signal handlers to release the lock on termination
                self._register_signal_handlers()
                
                return True
            
            # Lock is already held by someone else
            try:
                current_owner = self.redis.get(self.lock_name)
                logger.warning(f"Lock already held by {current_owner}, retry {attempt+1}/{self.max_retries}")
            except:
                logger.warning(f"Lock already held, retry {attempt+1}/{self.max_retries}")
            
            # Wait before retrying
            time.sleep(self.retry_interval)
        
        logger.error(f"Failed to acquire lock '{self.lock_name}' after {self.max_retries} attempts")
        return False
    
    def release(self):
        """
        Release the lock if we own it.
        
        Returns:
            bool: True if the lock was released, False otherwise
        """
        if not self.locked:
            logger.warning("Cannot release lock - not currently held")
            return False
        
        if not self.connect():
            logger.error("Cannot release lock - Redis connection failed")
            return False
        
        try:
            # Check if we still own the lock
            current_value = self.redis.get(self.lock_name)
            if current_value and current_value.decode('utf-8') == self.lock_id:
                # We still own the lock, delete it
                self.redis.delete(self.lock_name)
                logger.info(f"Lock '{self.lock_name}' released successfully")
                self.locked = False
                self._stop_heartbeat()
                return True
            else:
                logger.warning(f"Cannot release lock '{self.lock_name}' - no longer owned by this process")
                self.locked = False
                self._stop_heartbeat()
                return False
                
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            return False
    
    def _register_signal_handlers(self):
        """Register signal handlers to release lock on termination"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, releasing lock")
            self.release()
            # Re-raise the signal after releasing the lock
            signal.signal(sig, signal.SIG_DFL)
            os.kill(os.getpid(), sig)
        
        for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            signal.signal(sig, signal_handler)
    
    def _heartbeat(self):
        """Refresh the lock TTL to prevent expiration while process is still alive"""
        import threading
        
        while self._heartbeat_running and self.locked:
            try:
                if self.connect():
                    # Check if we still own the lock
                    current_value = self.redis.get(self.lock_name)
                    if current_value and current_value.decode('utf-8') == self.lock_id:
                        # Refresh the TTL
                        self.redis.expire(self.lock_name, self.ttl)
                        logger.debug(f"Lock '{self.lock_name}' heartbeat sent")
                    else:
                        logger.warning("Lock ownership lost during heartbeat!")
                        self.locked = False
                        self._heartbeat_running = False
                        break
            except Exception as e:
                logger.error(f"Error in lock heartbeat: {str(e)}")
            
            # Sleep for half the TTL time
            time.sleep(self.ttl / 2)
    
    def _start_heartbeat(self):
        """Start the heartbeat thread"""
        import threading
        
        if not self._heartbeat_running:
            self._heartbeat_running = True
            threading.Thread(target=self._heartbeat, daemon=True).start()
            logger.debug("Lock heartbeat thread started")
    
    def _stop_heartbeat(self):
        """Stop the heartbeat thread"""
        self._heartbeat_running = False
        logger.debug("Lock heartbeat thread stopped")
    
    def __enter__(self):
        """Context manager support - acquire lock on enter"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support - release lock on exit"""
        self.release()
        
def check_and_terminate_duplicates():
    """
    Check for duplicate bot processes and terminate them.
    Used before attempting to acquire the Redis lock.
    """
    try:
        import psutil
        current_pid = os.getpid()
        bot_processes = []
        
        logger.info(f"Scanning for duplicate bot processes (current PID: {current_pid})")
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip current process
                if proc.info['pid'] == current_pid:
                    continue
                
                # Look for Python processes running our bot
                cmd = ' '.join(proc.info['cmdline'] or [])
                if proc.info['name'] in ('python', 'python3') and ('bot.py' in cmd or 'start.py' in cmd):
                    bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Terminate duplicate processes if found
        if bot_processes:
            logger.warning(f"Found {len(bot_processes)} duplicate bot processes! Terminating...")
            for proc in bot_processes:
                try:
                    proc_pid = proc.info['pid']
                    proc.kill()
                    logger.info(f"Terminated duplicate bot process with PID {proc_pid}")
                except Exception as e:
                    logger.error(f"Failed to terminate process {proc.info['pid']}: {e}")
        else:
            logger.info("No duplicate bot processes found")
            
    except ImportError:
        logger.warning("psutil module not available - skipping duplicate process check")
    except Exception as e:
        logger.error(f"Error checking for duplicate processes: {e}")

def main():
    """Test the Redis lock functionality"""
    # Configure Redis URL from environment or use default
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Check for and terminate duplicate processes
    check_and_terminate_duplicates()
    
    # Create and test the lock
    lock = RedisLock(redis_url=redis_url, lock_name="dostup_bot_test_lock")
    
    if lock.acquire():
        print(f"Lock acquired by {lock.lock_id}")
        try:
            print("Press Ctrl+C to release lock and exit")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            lock.release()
    else:
        print("Failed to acquire lock")

if __name__ == "__main__":
    main()
