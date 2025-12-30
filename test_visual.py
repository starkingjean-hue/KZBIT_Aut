"""
KZBIT Automation - Visual Test (Non-Headless)

Runs the workflow with a VISIBLE browser window so you can see
exactly what the bot is doing in real-time.

Usage:
    python test_visual.py
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
import json
import time

from screenshot import ensure_screenshots_dir, ScreenshotCapture, clear_screenshots_dir
from config import KZBIT_LOGIN_URL, KZBIT_BTC_URL, SELECTORS, ACCOUNTS_FILE
from account_manager import AccountManager
from popup_monitor import PopupMonitor


async def test_visual_workflow():
    """
    Test the workflow with a VISIBLE browser.
    
    This allows you to see exactly what the bot does:
    [1] Login page navigation
    [2] Form filling
    [3] BTC page navigation
    [4] Code submission simulation
    """
    print("=" * 60)
    print("🔍 KZBIT VISUAL TEST (Non-Headless)")
    print("=" * 60)
    print()
    print("⚠️  Le navigateur sera VISIBLE")
    print("    Observez les actions en temps réel")
    print()
    
    # [0] Clear previous screenshots
    print("🧹 Nettoyage des anciens screenshots...")
    clear_screenshots_dir()
    screenshots_dir = ensure_screenshots_dir()
    
    start_time_total = time.perf_counter()
    
    async with async_playwright() as p:
        # Launch browser in VISIBLE mode (headless=False)
        browser = await p.chromium.launch(
            headless=False,  # 👁️ VISIBLE BROWSER
            slow_mo=500,     # Ralentir les actions pour mieux voir
            args=[
                "--start-maximized",
            ]
        )
        
        # Create context with larger viewport
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        
        page = await context.new_page()
        capture = ScreenshotCapture(page, "visual_test", enabled=True)
        monitor = PopupMonitor(page)
        
        try:
            # ================================================================
            # [1] LOGIN PAGE
            # ================================================================
            print("\n" + "─" * 50)
            print("📍 [1] LOGIN PAGE - Observez le navigateur...")
            print("─" * 50)
            
            await page.goto(KZBIT_LOGIN_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # Pause pour observer
            
            await capture.capture_login_page()
            print(f"   ✅ URL: {page.url}")
            
            # Load real credentials from accounts.json
            manager = AccountManager(ACCOUNTS_FILE)
            try:
                manager.load_accounts()
                if manager.accounts:
                    account = manager.accounts[0]
                    email = account.email
                    password = account.password
                    print(f"   👤 Utilisation du compte: {email}")
                else:
                    print("   ⚠️ Aucun compte dans accounts.json, utilisation des démos")
                    email = "demo@example.com"
                    password = "demopassword123"
            except Exception as e:
                print(f"   ⚠️ Erreur chargement accounts.json: {e}")
                email = "demo@example.com"
                password = "demopassword123"

            # Fill credentials
            try:
                email_input = await page.wait_for_selector(
                    SELECTORS["email_input"],
                    timeout=5000
                )
                if email_input:
                    print(f"   ⌨️ Remplissage email: {email}")
                    await email_input.fill(email)
                    await asyncio.sleep(0.5)
                
                password_input = await page.wait_for_selector(
                    SELECTORS["password_input"],
                    timeout=5000
                )
                if password_input:
                    print("   ⌨️ Remplissage mot de passe...")
                    await password_input.fill(password)
                    await asyncio.sleep(0.5)
                
                await capture.capture_credentials_filled()
                print("   ✅ Identifiants remplis")
                
                # [1c] Click Sign In button (Enter key is NOT supported)
                login_btn = await page.wait_for_selector(
                    SELECTORS["login_button"],
                    timeout=5000
                )
                if login_btn:
                    print("   🔘 Clic sur Sign in...")
                    await login_btn.click()
                    
                    # Wait for and read login popup
                    popup_text, status = await monitor.wait_and_read()
                    print(f"   💬 Popup Login: {popup_text}")
                    
                    # Verify success keyword
                    success_keywords = ["successful", "success", "réussi", "bienvenue", "welcome"]
                    if any(kw in popup_text.lower() for kw in success_keywords):
                        print("   ✅ Confirmation de connexion via popup")
                    else:
                        print(f"   ❌ Échec confirmation login (Probablement identifiants invalides)")
                    
                    # Wait for navigation
                    try:
                        await page.wait_for_url(lambda url: "login" not in url.lower(), timeout=10000)
                        print("   ✅ Changement d'URL détecté")
                    except:
                        print("   ⚠️ Toujours sur la page de login")
                
            except Exception as e:
                print(f"   ⚠️ Échec login: {e}")
            
            # ================================================================
            # [2] HOME PAGE (simulated)
            # ================================================================
            print("\n" + "─" * 50)
            print("📍 [2] HOME PAGE - État après connexion")
            print("─" * 50)
            
            await capture.capture_home_page()
            await asyncio.sleep(1)
            
            # ================================================================
            # [3] BTC PAGE
            # ================================================================
            print("\n" + "─" * 50)
            print("📍 [3] BTC PAGE - Navigation directe")
            print("─" * 50)
            
            print(f"   🌐 Navigation vers: {KZBIT_BTC_URL}")
            await page.goto(KZBIT_BTC_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # CHECK: Did we get redirected back to login?
            if "login" in page.url.lower():
                print("   ❌ Redirigé vers login : Session expirée ou échec de connexion")
                await capture.capture_error("Navigation_Redirect")
            else:
                await capture.capture_btc_page()
                print(f"   ✅ URL BTC chargée: {page.url}")
                
                # Try to find code input
                try:
                    code_input = await page.wait_for_selector(
                        SELECTORS["code_input"],
                        timeout=5000
                    )
                    if code_input:
                        print(f"   ⌨️ Saisie du code test: 2ff")
                        await code_input.fill("2ff")
                        await asyncio.sleep(0.5)
                        
                        await capture.capture_btc_input_code(1)
                        print("   ✅ Code saisi: 2ff")
                        
                        # Find submit button and actually click it (ROBUST)
                        print("   🔘 Recherche du bouton Submit...")
                        submit_btn = None
                        selectors_to_try = [
                            SELECTORS["submit_button"],
                            SELECTORS["submit_button_alt"]
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                submit_btn = await page.wait_for_selector(
                                    selector,
                                    state="visible",
                                    timeout=2000
                                )
                                if submit_btn:
                                    print(f"   ✅ Bouton trouvé avec: {selector}")
                                    break
                            except:
                                continue
                        
                        if not submit_btn:
                            print("   ⚠️ Tentative finale avec le sélecteur par défaut...")
                            submit_btn = await page.wait_for_selector(
                                SELECTORS["submit_button"],
                                timeout=5000
                            )

                        if submit_btn:
                            print("   🔘 Clic sur Submit...")
                            await submit_btn.click()
                            
                            # Wait for and read submit popup
                            popup_text, status = await monitor.wait_and_read()
                            print(f"   💬 Popup Submit: {popup_text} (Statut: {status.value})")
                            
                            await capture.capture_btc_popup_message(1)
                        
                except Exception as e:
                    print(f"   ⚠️ Échec submission: {e}")
            
            # Final screenshot
            await capture.capture("Final_State")
            
            # ================================================================
            # PAUSE AVANT FERMETURE
            # ================================================================
            print("\n" + "─" * 50)
            print("⏸️  PAUSE - Examinez le navigateur...")
            print("   Le navigateur se fermera dans 5 secondes")
            print("─" * 50)
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            await capture.capture_error("test")
            await asyncio.sleep(3)
            
        finally:
            await context.close()
            await browser.close()
    
    # ================================================================
    # SUMMARY
    # ================================================================
    total_duration = time.perf_counter() - start_time_total
    
    print("\n" + "=" * 60)
    print("✅ Test visuel terminé!")
    print(f"⏱️  Durée totale : {total_duration:.2f} secondes")
    print("=" * 60)
    
    print("\n📸 Screenshots capturés:")
    for f in sorted(screenshots_dir.glob("visual_test_*.png")):
        size_kb = f.stat().st_size / 1024
        print(f"   📷 {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(test_visual_workflow())
