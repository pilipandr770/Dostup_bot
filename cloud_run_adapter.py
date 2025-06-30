import os
import sys
import logging
from threading import Thread
import asyncio
from aiohttp import web
import traceback
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cloud_run_adapter")

def init_cloud_run_adapter(bot_main_func):
    """
    Initialize Cloud Run adapter to make the Telegram bot work in Cloud Run environment
    
    Args:
        bot_main_func: The main function of the bot that starts the polling
    """
    logger.info("Initializing Cloud Run adapter")
    
    # Log Python path for debugging
    logger.info("Python path:")
    for path in sys.path:
        logger.info(f"  - {path}")
    
    # Log environment variables
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if key in ["BOT_TOKEN", "ADMIN_USER_ID", "COURSE_CHANNEL_ID"]:
            # Mask sensitive values but show if they're set
            logger.info(f"  - {key}: {'[SET]' if value else '[NOT SET]'}")
        else:
            logger.info(f"  - {key}: {value}")
    
    # Get port from environment variable
    port = int(os.getenv("PORT", 8080))
    
    # Create a simple web app to handle health checks
    async def health_handler(request):
        return web.Response(text="Bot is running")
    
    async def debug_handler(request):
        # Return detailed debug information
        debug_info = {
            "python_path": sys.path,
            "current_directory": os.getcwd(),
            "files_in_app": os.listdir('/app') if os.path.exists('/app') else "Not available",
            "environment_vars": {k: ('[SET]' if k in ["BOT_TOKEN", "ADMIN_USER_ID"] else v) for k, v in os.environ.items()}
        }
        return web.json_response(debug_info)
    
    async def run_web_server():
        app = web.Application()
        app.router.add_get("/", health_handler)
        app.router.add_get("/health", health_handler)
        app.router.add_get("/debug", debug_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        
        try:
            await site.start()
            logger.info(f"Web server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            logger.error(traceback.format_exc())
            # Re-raise to fail the container startup if web server can't start
            raise
        
        while True:
            await asyncio.sleep(3600)  # Keep the web server running indefinitely
    
    def run_bot_with_retry():
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Starting bot (attempt {retry_count + 1})")
                bot_main_func()
                logger.info("Bot exited normally")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Bot crashed with error: {e}")
                logger.error(traceback.format_exc())
                if retry_count < max_retries:
                    sleep_time = min(60, 5 * retry_count)  # Exponential backoff
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error("Maximum retry attempts reached. Bot will not be restarted.")
                    # Don't exit - let the container keep running for health checks
    
    async def start_services():
        # Start the web server for health checks
        web_server_task = asyncio.create_task(run_web_server())
        
        # Start the bot in a separate task with retry logic
        loop = asyncio.get_event_loop()
        bot_task = loop.run_in_executor(None, run_bot_with_retry)
        
        # Wait for both tasks - but we'll keep the web server running even if bot fails
        try:
            await asyncio.gather(web_server_task, bot_task)
        except Exception as e:
            logger.error(f"Error in service tasks: {e}")
            logger.error(traceback.format_exc())
            # Keep the web server running even if there's an error
            await web_server_task
    
    # Run everything in the main event loop
    logger.info("Starting Cloud Run adapter")
    try:
        asyncio.run(start_services())
    except Exception as e:
        logger.error(f"Fatal error in Cloud Run adapter: {e}")
        logger.error(traceback.format_exc())
        # Don't exit - we need to keep the container running for health checks
        # Just run a minimal web server
        async def run_minimal_server():
            app = web.Application()
            app.router.add_get("/", lambda r: web.Response(text="Emergency health check endpoint"))
            app.router.add_get("/health", lambda r: web.Response(text="Emergency health check endpoint"))
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            logger.info(f"Emergency web server started on port {port}")
            
            while True:
                await asyncio.sleep(3600)
        
        asyncio.run(run_minimal_server())
