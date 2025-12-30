"""
KZBIT Automation - Popup Monitor Module

Handles detection and classification of ephemeral popup messages.
Uses intelligent waits instead of static sleeps.
"""

import asyncio
from typing import Optional, Tuple

from playwright.async_api import Page

from config import SELECTORS, POPUP_TIMEOUT, SUCCESS_PATTERNS, ERROR_PATTERNS
from models import PopupStatus


class PopupMonitor:
    """
    Monitor and extract popup messages from the page.
    
    The popup appears briefly after form submission.
    Must detect and read it immediately.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self._selector = SELECTORS["popup"]
    
    async def wait_and_read(
        self,
        timeout_ms: int = POPUP_TIMEOUT
    ) -> Tuple[str, PopupStatus]:
        """
        Wait for popup to appear)and read its content.
        
        Args:
            timeout_ms: Maximum time to wait for popup
            
        Returns:
            Tuple of (popup_text, classification)
        """
        try:
            # Wait for popup element to appear
            popup = await self.page.wait_for_selector(
                self._selector,
                state="visible",
                timeout=timeout_ms
            )
            
            if popup is None:
                return ("No popup detected", PopupStatus.UNKNOWN)
            
            # Extract text content
            text = await popup.text_content() or ""
            text = text.strip()
            
            # Classify the message
            status = self._classify(text)
            
            return (text, status)
            
        except Exception as e:
            return (f"Popup detection failed: {e}", PopupStatus.UNKNOWN)
    
    async def wait_and_read_with_observer(
        self,
        timeout_ms: int = POPUP_TIMEOUT
    ) -> Tuple[str, PopupStatus]:
        """
        Alternative: Use MutationObserver for instant detection.
        
        This injects JavaScript to observe DOM changes.
        More reliable for very fast popups.
        """
        try:
            # Inject observer and wait for popup
            result = await self.page.evaluate(f"""
                () => new Promise((resolve, reject) => {{
                    const timeout = setTimeout(() => {{
                        resolve({{ text: 'Timeout waiting for popup', found: false }});
                    }}, {timeout_ms});
                    
                    const observer = new MutationObserver((mutations) => {{
                        for (const mutation of mutations) {{
                            for (const node of mutation.addedNodes) {{
                                if (node.nodeType === 1) {{
                                    const popup = node.matches('{self._selector}') 
                                        ? node 
                                        : node.querySelector('{self._selector}');
                                    if (popup) {{
                                        clearTimeout(timeout);
                                        observer.disconnect();
                                        resolve({{ text: popup.textContent.trim(), found: true }});
                                        return;
                                    }}
                                }}
                            }}
                        }}
                    }});
                    
                    // Check if popup already exists
                    const existing = document.querySelector('{self._selector}');
                    if (existing) {{
                        clearTimeout(timeout);
                        resolve({{ text: existing.textContent.trim(), found: true }});
                        return;
                    }}
                    
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true
                    }});
                }})
            """)
            
            text = result.get("text", "")
            found = result.get("found", False)
            
            if not found:
                return (text, PopupStatus.UNKNOWN)
            
            status = self._classify(text)
            return (text, status)
            
        except Exception as e:
            return (f"Observer failed: {e}", PopupStatus.UNKNOWN)
    
    def _classify(self, text: str) -> PopupStatus:
        """
        Classify popup message as success/error/unknown.
        
        Uses pattern matching against known keywords.
        """
        text_lower = text.lower()
        
        # Check for success patterns
        for pattern in SUCCESS_PATTERNS:
            if pattern in text_lower:
                return PopupStatus.SUCCESS
        
        # Check for error patterns
        for pattern in ERROR_PATTERNS:
            if pattern in text_lower:
                return PopupStatus.ERROR
        
        return PopupStatus.UNKNOWN


async def read_popup(page: Page, timeout_ms: int = POPUP_TIMEOUT) -> Tuple[str, PopupStatus]:
    """
    Convenience function to read popup from page.
    
    Args:
        page: Playwright page instance
        timeout_ms: Maximum wait time
        
    Returns:
        Tuple of (text, status)
    """
    monitor = PopupMonitor(page)
    return await monitor.wait_and_read(timeout_ms)
