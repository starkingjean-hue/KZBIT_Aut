"""
KZBIT Automation - Screenshot Capture Module

Captures screenshots at each automation step with specific naming:
- Login_Page.png
- Home_Page.png
- BTC_Input_Code.png
- BTC_Click_Submit.png
- BTC_Popup_Message.png
- BTC_Repetition.png
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Page

from config import BASE_DIR


# Screenshots directory
SCREENSHOTS_DIR = BASE_DIR / "screenshots"


def ensure_screenshots_dir() -> Path:
    """Create screenshots directory if it doesn't exist."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    return SCREENSHOTS_DIR


def clear_screenshots_dir():
    """Remove all PNG files from the screenshots directory."""
    if SCREENSHOTS_DIR.exists():
        for f in SCREENSHOTS_DIR.glob("*.png"):
            try:
                f.unlink()
            except Exception as e:
                print(f"⚠️ Could not delete {f.name}: {e}")
    else:
        ensure_screenshots_dir()


def generate_filename(account_email: str, action: str, suffix: str = "") -> str:
    """
    Generate a filename for a screenshot.
    
    Uses the exact naming convention requested.
    """
    # Sanitize email for filename
    account_safe = account_email.split("@")[0].replace(".", "_")[:15]
    
    if suffix:
        return f"{account_safe}_{action}_{suffix}.png"
    return f"{account_safe}_{action}.png"


class ScreenshotCapture:
    """
    Screenshot capture utility for automation steps.
    
    Captures with specific naming:
    [1] Login_Page.png - Page de login
    [2] Home_Page.png - Après connexion  
    [3] BTC_Input_Code.png - Code saisi
    [4] BTC_Click_Submit.png - Après clic submit
    [5] BTC_Popup_Message.png - Popup visible
    [6] BTC_Repetition.png - Répétition N
    """
    
    def __init__(self, page: Page, account_email: str, enabled: bool = True):
        self.page = page
        self.account_email = account_email
        self.enabled = enabled
        self.screenshots: list[Path] = []
        
        if enabled:
            ensure_screenshots_dir()
    
    async def capture(self, action: str, suffix: str = "") -> Optional[Path]:
        """
        Capture a screenshot with the given action name.
        
        Args:
            action: Name of the current action
            suffix: Optional suffix for multiple screenshots
            
        Returns:
            Path to saved screenshot, or None if disabled
        """
        if not self.enabled:
            return None
        
        try:
            filename = generate_filename(self.account_email, action, suffix)
            filepath = SCREENSHOTS_DIR / filename
            
            await self.page.screenshot(path=str(filepath), full_page=False)
            
            self.screenshots.append(filepath)
            print(f"📸 Screenshot: {filename}")
            
            return filepath
            
        except Exception as e:
            print(f"⚠️ Screenshot failed ({action}): {e}")
            return None
    
    # ========================================================================
    # STEP 1: LOGIN PAGE
    # ========================================================================
    
    async def capture_login_page(self) -> Optional[Path]:
        """[1] Capture login page - Login_Page.png"""
        return await self.capture("Login_Page")
    
    async def capture_credentials_filled(self) -> Optional[Path]:
        """[1b] Capture after credentials filled"""
        return await self.capture("Login_Credentials_Filled")
    
    # ========================================================================
    # STEP 2: HOME PAGE (after login)
    # ========================================================================
    
    async def capture_home_page(self) -> Optional[Path]:
        """[2] Capture home page after login - Home_Page.png"""
        return await self.capture("Home_Page")
    
    # ========================================================================
    # STEP 3: BTC PAGE
    # ========================================================================
    
    async def capture_btc_page(self) -> Optional[Path]:
        """[3] Capture BTC trade page loaded"""
        return await self.capture("BTC_Page")
    
    async def capture_btc_input_code(self, submit_num: int) -> Optional[Path]:
        """[3a] Capture after code pasted - BTC_Input_Code.png"""
        return await self.capture("BTC_Input_Code", f"submit{submit_num}")
    
    async def capture_btc_click_submit(self, submit_num: int) -> Optional[Path]:
        """[3b] Capture after clicking submit - BTC_Click_Submit.png"""
        return await self.capture("BTC_Click_Submit", f"submit{submit_num}")
    
    async def capture_btc_popup_message(self, submit_num: int) -> Optional[Path]:
        """[3c] Capture popup message - BTC_Popup_Message.png"""
        return await self.capture("BTC_Popup_Message", f"submit{submit_num}")
    
    async def capture_btc_repetition(self, submit_num: int, total: int) -> Optional[Path]:
        """[3d] Capture repetition state - BTC_Repetition.png"""
        return await self.capture("BTC_Repetition", f"{submit_num}_of_{total}")
    
    # ========================================================================
    # ERROR STATES
    # ========================================================================
    
    async def capture_error(self, step: str) -> Optional[Path]:
        """Capture error state at any step."""
        return await self.capture(f"Error_{step}")
    
    def get_all_screenshots(self) -> list[Path]:
        """Return list of all captured screenshots."""
        return self.screenshots.copy()
