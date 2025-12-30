"""
KZBIT Automation - Core Automation Module

The heart of the system: login, navigation, and code submission.
Optimized for speed with direct URL navigation and minimal waits.

Screenshot capture at each step:
[1] Login_Page.png - Page de login
[2] Home_Page.png - Après connexion
[3] BTC_Input_Code.png - Code saisi
[4] BTC_Click_Submit.png - Après clic submit
[5] BTC_Popup_Message.png - Popup visible
[6] BTC_Repetition.png - Répétition N
"""

import asyncio
import time
from typing import List, Optional
from pathlib import Path

from playwright.async_api import Page

from config import (
    KZBIT_LOGIN_URL,
    KZBIT_BTC_URL,
    SELECTORS,
    ELEMENT_TIMEOUT,
    SUBMIT_TIMEOUT,
    POPUP_TIMEOUT,
)
from models import Account, SubmitResult, AccountResult, PopupStatus
from popup_monitor import PopupMonitor
from timing import AccountTimer, get_global_deadline
from screenshot import ScreenshotCapture


class KZBITAutomation:
    """
    Core automation workflow for a single KZBIT account.
    
    Workflow with screenshots:
    [1] Login → Login_Page.png, Home_Page.png
    [2] Navigate to BTC → BTC_Page.png
    [3] Submit code N times → BTC_Input_Code.png, BTC_Click_Submit.png, 
                              BTC_Popup_Message.png, BTC_Repetition.png
    """
    
    def __init__(
        self,
        page: Page,
        account: Account,
        timer: AccountTimer,
        capture_screenshots: bool = True
    ):
        self.page = page
        self.account = account
        self.timer = timer
        self.popup_monitor = PopupMonitor(page)
        self.screenshot = ScreenshotCapture(
            page,
            account.email,
            enabled=capture_screenshots
        )
    
    async def login(self) -> bool:
        """
        [1] Perform login on kzbit.com.
        
        Screenshots:
        - Login_Page.png: Page de login chargée
        - Login_Credentials_Filled.png: Identifiants remplis
        - Home_Page.png: Après connexion réussie
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            async with self.timer.timed_operation("login") as t:
                # Navigate to login page
                await self.page.goto(
                    KZBIT_LOGIN_URL,
                    wait_until="domcontentloaded"
                )
                
                # 📸 [1] Login_Page.png
                await self.screenshot.capture_login_page()
                
                # Fill email
                email_input = await self.page.wait_for_selector(
                    SELECTORS["email_input"],
                    state="visible",
                    timeout=ELEMENT_TIMEOUT
                )
                await email_input.fill(self.account.email)
                
                # Fill password
                password_input = await self.page.wait_for_selector(
                    SELECTORS["password_input"],
                    state="visible",
                    timeout=ELEMENT_TIMEOUT
                )
                await password_input.fill(self.account.password)
                
                # IMMEDIATE SUBMIT
                await password_input.press("Enter")
                
                # Ultra-fast check for movement
                try:
                    # Very short timeout to see if Enter worked
                    await self.page.wait_for_url(lambda u: "login" not in u.lower(), timeout=1000)
                except:
                    # If not moved, force click the button with NO delay
                    try:
                        await self.page.click(SELECTORS["login_button"], force=True, no_wait_after=True, timeout=1000)
                    except:
                        pass

                # Pre-emptive navigation to BTC page while popup might be appearing
                # We skip waiting for popup if URL already changed to index/home
                current_url = self.page.url.lower()
                if "login" in current_url:
                    # If still on login, wait short for popup
                    try:
                        popup_text, status = await self.popup_monitor.wait_and_read(timeout_ms=3000)
                    except:
                        popup_text = "ERROR_TIMEOUT"
                else:
                    popup_text = "Success (Auto-detected)"

                # Direct verification of session
                is_actually_logged_in = "login" not in self.page.url.lower()
                
                if not is_actually_logged_in:
                    # Final check popup content
                    success_keywords = ["successful", "success", "réussi", "bienvenue", "welcome"]
                    is_actually_logged_in = any(kw in popup_text.lower() for kw in success_keywords)

                if not is_actually_logged_in:
                    return False

                # SKIP Home Page screenshot for speed
                # await self.screenshot.capture_home_page()
            
            self.timer.metrics.login_ms = t.elapsed_ms
            return True
            
        except Exception as e:
            print(f"[{self.account.email}] Login failed: {e}")
            await self.screenshot.capture_error("Login")
            return False
    
    async def navigate_to_btc(self) -> bool:
        """
        [3] Force navigate directly to BTC trade page.
        
        Direct URL navigation - no UI interaction.
        Detects if redirected back to login (session failed).
        
        Screenshots:
        - BTC_Page.png: Page BTC chargée
        
        Returns:
            True if navigation successful and session is active
        """
        try:
            async with self.timer.timed_operation("navigation") as t:
                await self.page.goto(
                    KZBIT_BTC_URL,
                    wait_until="domcontentloaded"
                )
                
                # CHECK: Did we get redirected back to login?
                if "login" in self.page.url.lower():
                    print(f"[{self.account.email}] Redirected to Login page from BTC. Session expired or failed.")
                    return False

                # Verify we're on the right page by looking for the input
                await self.page.wait_for_selector(
                    SELECTORS["code_input"],
                    state="visible",
                    timeout=ELEMENT_TIMEOUT
                )
                
                # 📸 BTC_Page.png
                await self.screenshot.capture_btc_page()
            
            self.timer.metrics.navigation_ms = t.elapsed_ms
            return True
            
        except Exception as e:
            print(f"[{self.account.email}] Navigation failed: {e}")
            await self.screenshot.capture_error("Navigation")
            return False
    
    async def submit_code(self, code: str, submit_num: int, total_submits: int) -> SubmitResult:
        """
        Submit a single BTC order code.
        
        Handles:
        - Robust button detection (trying multiple selectors)
        - Page load verification
        - Redirect detection (session loss)
        """
        start_time = time.perf_counter()
        
        try:
            self.timer.check()
            
            # 1. Verification d'état de la page
            # Attendre que la page soit stable
            await self.page.wait_for_load_state("domcontentloaded")
            
            # CHECK: Did we get redirected back to login?
            if "login" in self.page.url.lower():
                print(f"[{self.account.email}] Session loss detected during submit. Redirected to Login.")
                return SubmitResult(
                    success=False,
                    popup_text="Session expirée (redirigé vers login)",
                    status=PopupStatus.ERROR,
                    duration_ms=0
                )

            # 2. Find and fill code input
            code_input = await self.page.wait_for_selector(
                SELECTORS["code_input"],
                state="visible",
                timeout=ELEMENT_TIMEOUT
            )
            
            # Clear and fill code
            await code_input.fill("")
            await code_input.fill(code)
            
            # 📸 BTC_Input_Code.png - Code collé (Désactivé pour vitesse)
            # await self.screenshot.capture_btc_input_code(submit_num)
            
            # 3. Find and click submit button (ROBUST & FAST)
            try:
                # Try the primary selector first with no wait
                submit_button = await self.page.wait_for_selector(SELECTORS["submit_button"], state="visible", timeout=1000)
            except:
                # Fallback to secondary immediately
                try:
                    submit_button = await self.page.wait_for_selector(SELECTORS["submit_button_alt"], state="visible", timeout=1000)
                except:
                    # Final attempt with main
                    submit_button = await self.page.wait_for_selector(SELECTORS["submit_button"], state="visible", timeout=2000)

            await submit_button.click(no_wait_after=True)
            
            # 4. Wait for and read popup (Fast detection)
            popup_text, status = await self.popup_monitor.wait_and_read(timeout_ms=3000)
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self.timer.metrics.submits_ms.append(duration_ms)
            
            return SubmitResult(
                success=(status == PopupStatus.SUCCESS),
                popup_text=popup_text,
                status=status,
                duration_ms=duration_ms
            )
            
        except TimeoutError as e:
            # Re-raise to be handled by caller
            raise
            
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            print(f"[{self.account.email}] Submit error: {e}")
            return SubmitResult(
                success=False,
                popup_text=f"Submit error: {e}",
                status=PopupStatus.ERROR,
                duration_ms=duration_ms
            )
    
    async def submit_code_n_times(self, code: str, n: int) -> List[SubmitResult]:
        """
        Submit the code N times in rapid succession.
        
        Pipeline: submit → popup → submit → popup ...
        """
        results = []
        
        for i in range(n):
            try:
                self.timer.check()
                result = await self.submit_code(code, submit_num=i+1, total_submits=n)
                results.append(result)
                
                print(
                    f"[{self.account.email}] Submit {i+1}/{n}: "
                    f"{result.status.value} - {result.popup_text} "
                    f"({result.duration_ms}ms)"
                )
                
            except TimeoutError as e:
                print(f"[{self.account.email}] Timeout: {e}")
                break
                
            except Exception as e:
                print(f"[{self.account.email}] Submit error: {e}")
                results.append(SubmitResult(
                    success=False,
                    popup_text=str(e),
                    status=PopupStatus.ERROR,
                    duration_ms=0
                ))
        
        return results
    
    async def run(self, code: str, clicks: int) -> AccountResult:
        """
        Execute the full workflow for this account.
        
        Steps:
        [1] Login → Login_Page.png, Home_Page.png
        [2] Navigate to BTC → BTC_Page.png
        [3] Submit code N times → BTC_Input_Code.png, BTC_Click_Submit.png,
                                  BTC_Popup_Message.png, BTC_Repetition.png
        """
        self.timer.start()
        results: List[SubmitResult] = []
        error: str = None
        
        try:
            # [1] Login
            if not await self.login():
                error = "Login failed"
                return self._build_result(results, clicks, error)
            
            # [2] Navigate to BTC
            if not await self.navigate_to_btc():
                error = "Navigation failed"
                return self._build_result(results, clicks, error)
            
            # [3] Submit N times
            results = await self.submit_code_n_times(code, clicks)
            
        except TimeoutError as e:
            error = str(e)
        except Exception as e:
            error = f"Unexpected error: {e}"
        finally:
            self.timer.finalize()
        
        return self._build_result(results, clicks, error)
    
    def _build_result(
        self,
        results: List[SubmitResult],
        target_submits: int,
        error: str = None
    ) -> AccountResult:
        """Build the final AccountResult."""
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        # A true success requires:
        # 1. No fatal error
        # 2. At least one submission attempted
        # 3. Number of attempted submissions matches target
        # 4. All attempted submissions were successful
        is_true_success = (
            error is None and 
            len(results) > 0 and 
            len(results) == target_submits and 
            successful == target_submits
        )
        
        return AccountResult(
            email=self.account.email,
            success=is_true_success,
            total_submits=len(results),
            successful_submits=successful,
            failed_submits=failed,
            duration_seconds=self.timer.elapsed_seconds,
            results=results,
            error=error
        )
    
    def get_screenshots(self) -> List[Path]:
        """Return all captured screenshots for this account."""
        return self.screenshot.get_all_screenshots()


async def process_account(
    page: Page,
    account: Account,
    code: str,
    clicks: int,
    capture_screenshots: bool = True
) -> AccountResult:
    """
    Convenience function to process a single account.
    """
    global_deadline = get_global_deadline()
    timer = AccountTimer(
        email=account.email,
        global_deadline=global_deadline
    )
    
    automation = KZBITAutomation(
        page,
        account,
        timer,
        capture_screenshots=capture_screenshots
    )
    result = await automation.run(code, clicks)
    
    print(f"[{account.email}] Completed: {timer.metrics}")
    print(f"[{account.email}] Screenshots: {len(automation.get_screenshots())} captured")
    
    return result
