"""
Auto Check-in/Check-out Tool for FE Credit HR Portal
=====================================================
Automatically clicks CHECK-IN or CHECK-OUT button on the HR portal.
"""

import os
import time
import schedule
import logging
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_checkin.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
HR_PORTAL_URL = os.getenv('HR_PORTAL_URL')
HR_USERNAME = os.getenv('HR_USERNAME')
HR_PASSWORD = os.getenv('HR_PASSWORD')
HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'


def create_driver():
    """Create and configure Chrome WebDriver."""
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    # Avoid detection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def login(driver):
    """Login to the HR Portal."""
    logger.info("Navigating to HR Portal...")
    driver.get(HR_PORTAL_URL)
    time.sleep(3)

    # Check if redirected to login page
    # Try to find username/email field
    try:
        # Wait for login form (adjust selectors based on actual login page)
        wait = WebDriverWait(driver, 15)

        # Try common login field selectors
        username_selectors = [
            (By.ID, 'username'),
            (By.ID, 'email'),
            (By.NAME, 'username'),
            (By.NAME, 'email'),
            (By.NAME, 'loginfmt'),  # Microsoft SSO
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.CSS_SELECTOR, 'input[type="text"]'),
        ]

        username_field = None
        for by, selector in username_selectors:
            try:
                username_field = wait.until(EC.presence_of_element_located((by, selector)))
                if username_field:
                    break
            except:
                continue

        if username_field:
            logger.info("Found login form, entering credentials...")
            username_field.clear()
            username_field.send_keys(HR_USERNAME)
            time.sleep(1)

            # Try to find and click Next button (for Microsoft SSO flow)
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
                next_btn.click()
                time.sleep(3)
            except:
                pass

            # Try to find password field
            password_selectors = [
                (By.ID, 'password'),
                (By.ID, 'passwordInput'),
                (By.NAME, 'password'),
                (By.NAME, 'passwd'),  # Microsoft SSO
                (By.CSS_SELECTOR, 'input[type="password"]'),
            ]

            password_field = None
            for by, selector in password_selectors:
                try:
                    password_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if password_field:
                        break
                except:
                    continue

            if password_field:
                password_field.clear()
                password_field.send_keys(HR_PASSWORD)
                time.sleep(1)

                # Click sign in button
                try:
                    signin_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
                    signin_btn.click()
                    time.sleep(3)
                except:
                    pass

            # Handle "Stay signed in?" prompt (Microsoft SSO)
            try:
                stay_signed_in = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, 'idSIButton9'))
                )
                stay_signed_in.click()
                time.sleep(3)
            except:
                pass

            logger.info("Login completed!")
        else:
            logger.info("No login form found - may already be logged in")

    except Exception as e:
        logger.warning(f"Login process encountered issue: {e}")
        logger.info("Continuing anyway - may already be authenticated...")


def perform_checkin(driver):
    """Click the CHECK-IN button."""
    try:
        wait = WebDriverWait(driver, 15)

        # Try multiple selectors for CHECK-IN button
        checkin_selectors = [
            (By.XPATH, "//button[contains(text(), 'CHECK-IN')]"),
            (By.XPATH, "//button[contains(text(), 'Check-in')]"),
            (By.XPATH, "//button[contains(text(), 'check-in')]"),
            (By.XPATH, "//*[contains(text(), 'CHECK-IN')]/ancestor::button"),
            (By.CSS_SELECTOR, "button.check-in"),
            (By.CSS_SELECTOR, "[class*='check-in']"),
            (By.CSS_SELECTOR, "button[color='primary']"),
        ]

        for by, selector in checkin_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((by, selector)))
                btn.click()
                logger.info("✅ CHECK-IN successful!")
                return True
            except:
                continue

        logger.warning("❌ Could not find CHECK-IN button")
        return False

    except Exception as e:
        logger.error(f"❌ CHECK-IN failed: {e}")
        return False


def perform_checkout(driver):
    """Click the CHECK-OUT button."""
    try:
        wait = WebDriverWait(driver, 15)

        # Try multiple selectors for CHECK-OUT button
        checkout_selectors = [
            (By.XPATH, "//button[contains(text(), 'CHECK-OUT')]"),
            (By.XPATH, "//button[contains(text(), 'Check-out')]"),
            (By.XPATH, "//button[contains(text(), 'check-out')]"),
            (By.XPATH, "//*[contains(text(), 'CHECK-OUT')]/ancestor::button"),
            (By.CSS_SELECTOR, "button.check-out"),
            (By.CSS_SELECTOR, "[class*='check-out']"),
            (By.CSS_SELECTOR, "button[color='warn']"),
        ]

        for by, selector in checkout_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((by, selector)))
                btn.click()
                logger.info("✅ CHECK-OUT successful!")
                return True
            except:
                continue

        logger.warning("❌ Could not find CHECK-OUT button")
        return False

    except Exception as e:
        logger.error(f"❌ CHECK-OUT failed: {e}")
        return False


def do_checkin():
    """Full check-in flow."""
    today = datetime.now()
    # Skip weekends
    if today.weekday() >= 5:  # Saturday=5, Sunday=6
        logger.info("Weekend - skipping check-in")
        return

    logger.info(f"=== Starting CHECK-IN at {today.strftime('%Y-%m-%d %H:%M:%S')} ===")
    driver = None
    try:
        driver = create_driver()
        login(driver)
        time.sleep(3)

        # Navigate to attendance page
        driver.get(HR_PORTAL_URL)
        time.sleep(5)

        perform_checkin(driver)
        time.sleep(3)

    except Exception as e:
        logger.error(f"Check-in error: {e}")
    finally:
        if driver:
            driver.quit()


def do_checkout():
    """Full check-out flow."""
    today = datetime.now()
    # Skip weekends
    if today.weekday() >= 5:
        logger.info("Weekend - skipping check-out")
        return

    logger.info(f"=== Starting CHECK-OUT at {today.strftime('%Y-%m-%d %H:%M:%S')} ===")
    driver = None
    try:
        driver = create_driver()
        login(driver)
        time.sleep(3)

        # Navigate to attendance page
        driver.get(HR_PORTAL_URL)
        time.sleep(5)

        perform_checkout(driver)
        time.sleep(3)

    except Exception as e:
        logger.error(f"Check-out error: {e}")
    finally:
        if driver:
            driver.quit()


def run_now(action='checkin'):
    """Run check-in or check-out immediately (for testing)."""
    if action == 'checkin':
        do_checkin()
    elif action == 'checkout':
        do_checkout()
    else:
        print(f"Unknown action: {action}. Use 'checkin' or 'checkout'.")


def run_scheduler():
    """Run the scheduler to auto check-in/check-out."""
    checkin_hour = int(os.getenv('CHECKIN_HOUR', 8))
    checkin_minute = int(os.getenv('CHECKIN_MINUTE', 0))
    checkout_hour = int(os.getenv('CHECKOUT_HOUR', 20))
    checkout_minute = int(os.getenv('CHECKOUT_MINUTE', 0))

    checkin_time = f"{checkin_hour:02d}:{checkin_minute:02d}"
    checkout_time = f"{checkout_hour:02d}:{checkout_minute:02d}"

    logger.info(f"📅 Scheduler started!")
    logger.info(f"   Check-in time:  {checkin_time}")
    logger.info(f"   Check-out time: {checkout_time}")
    logger.info(f"   Press Ctrl+C to stop")
    logger.info("")

    schedule.every().monday.at(checkin_time).do(do_checkin)
    schedule.every().tuesday.at(checkin_time).do(do_checkin)
    schedule.every().wednesday.at(checkin_time).do(do_checkin)
    schedule.every().thursday.at(checkin_time).do(do_checkin)
    schedule.every().friday.at(checkin_time).do(do_checkin)

    schedule.every().monday.at(checkout_time).do(do_checkout)
    schedule.every().tuesday.at(checkout_time).do(do_checkout)
    schedule.every().wednesday.at(checkout_time).do(do_checkout)
    schedule.every().thursday.at(checkout_time).do(do_checkout)
    schedule.every().friday.at(checkout_time).do(do_checkout)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == 'scheduler':
            run_scheduler()
        elif action in ('checkin', 'checkout'):
            run_now(action)
        else:
            print("Usage:")
            print("  python auto_checkin.py checkin    - Run check-in now")
            print("  python auto_checkin.py checkout   - Run check-out now")
            print("  python auto_checkin.py scheduler  - Start auto scheduler")
    else:
        print("FE Credit Auto Check-in Tool")
        print("=" * 40)
        print("")
        print("Commands:")
        print("  python auto_checkin.py checkin    - Check-in ngay")
        print("  python auto_checkin.py checkout   - Check-out ngay")
        print("  python auto_checkin.py scheduler  - Chay tu dong theo lich")
        print("")
        print(f"Config: Check-in {os.getenv('CHECKIN_HOUR', 8)}:{os.getenv('CHECKIN_MINUTE', '00').zfill(2)}")
        print(f"        Check-out {os.getenv('CHECKOUT_HOUR', 20)}:{os.getenv('CHECKOUT_MINUTE', '00').zfill(2)}")
