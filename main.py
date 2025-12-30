"""
KZBIT Automation - Main Entry Point

Starts the Telegram bot and handles graceful shutdown.
"""

import asyncio
import sys
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_bot import start_bot
from browser import cleanup_browser
from screenshot import clear_screenshots_dir


async def main() -> None:
    """
    Main entry point.
    Runs until interrupted.
    """
    print("=" * 60)
    print("KZBIT Automation System")
    print("=" * 60)
    print()
    
    bot = None
    try:
        # [0] Clear screenshots at start
        clear_screenshots_dir()
        
        # Start the bot
        bot = await start_bot()
        
        # Keep running
        await bot.run_forever()
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        # Cleanup
        print("Cleaning up...")
        if bot:
            await bot.stop()
        else:
            await cleanup_browser()
        print("Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
