"""
KZBIT Automation - Configuration Module

Centralized configuration with environment variable support.
All timeouts and selectors are defined here for easy tuning.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
LOGS_DIR = BASE_DIR / "logs"

# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ============================================================================
# KZBIT URLs - CORRECTED (.html not .htm)
# ============================================================================
KZBIT_LOGIN_URL = "https://kzbit.com/login/login.html"
KZBIT_HOME_URL = "https://kzbit.com/index/index.html"
KZBIT_BTC_URL = "https://kzbit.com/trade/index/id/4"

# ============================================================================
# CSS SELECTORS (optimized for speed)
# ============================================================================
SELECTORS = {
    # Login page
    "email_input": 'input[placeholder="Please enter email"]',
    "password_input": 'input[placeholder="Please enter your password"]',
    "login_button": 'button:has-text("Sign in"), input[type="submit"]',
    
    # BTC trade page
    "code_input": 'input[placeholder="Please enter the order code"]',
    "submit_button": 'button:has-text("Submit")',
    "submit_button_alt": '#gendan_btn',
    
    # Popup
    "popup": "div.dream-msg-content",
}

# ============================================================================
# TIMING CONFIGURATION (in seconds)
# ============================================================================
# Global deadline - CRITICAL: code expires after 10 minutes
GLOBAL_TIMEOUT = int(os.getenv("GLOBAL_TIMEOUT_SECONDS", "600"))

# Maximum time per account before skipping
ACCOUNT_TIMEOUT = int(os.getenv("ACCOUNT_TIMEOUT_SECONDS", "90"))

# Timeout for each submit operation
SUBMIT_TIMEOUT = int(os.getenv("SUBMIT_TIMEOUT_SECONDS", "5"))

# Short waits for page transitions
NAVIGATION_TIMEOUT = 10000  # ms - for page loads
ELEMENT_TIMEOUT = 5000      # ms - for element appearance
POPUP_TIMEOUT = 10000       # ms - for popup detection

# ============================================================================
# PARALLEL EXECUTION
# ============================================================================
MAX_CONCURRENT_ACCOUNTS = int(os.getenv("MAX_CONCURRENT_ACCOUNTS", "1"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# ============================================================================
# RESOURCE BLOCKING (for performance)
# ============================================================================
BLOCKED_RESOURCE_TYPES = ["image", "font", "media"]
BLOCKED_URL_PATTERNS = [
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    "*.mp4", "*.webm",
    "*google-analytics*", "*facebook*", "*twitter*",
]

# ============================================================================
# POPUP PATTERNS (for classification)
# ============================================================================
SUCCESS_PATTERNS = [
    "success",
    "successful",
    "completed",
    "réussi",
]

ERROR_PATTERNS = [
    "error",
    "failed",
    "invalid",
    "expired",
    "incorrect",
    "erreur",
]
