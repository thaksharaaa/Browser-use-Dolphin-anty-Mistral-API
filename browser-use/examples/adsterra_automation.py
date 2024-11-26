import os
import asyncio
import random
import time
from typing import Optional
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent, Controller, DolphinBrowser
from pydantic import BaseModel
import aiohttp

# Load environment variables
load_dotenv()

class AdsterraConfig(BaseModel):
    landing_url: str = "https://genuine-snickerdoodle-88333b.netlify.app"
    proxy_rotation_url: str
    browser_type: str = "anty"
    browser_version: str = "120"
    platform: str = "windows"
    min_session_time: int = 120  # 2 minutes minimum
    max_session_time: int = 600  # 10 minutes maximum
    min_ad_interaction_time: int = 30  # 30 seconds minimum for ad interaction
    max_ad_interaction_time: int = 90  # 90 seconds maximum for ad interaction

class AdsterraAutomation:
    def __init__(self):
        self.api_token = os.getenv("DOLPHIN_API_TOKEN")
        self.config = AdsterraConfig(
            proxy_rotation_url=os.getenv("PROXY_ROTATION_URL")
        )

    async def rotate_proxy(self, browser: DolphinBrowser) -> bool:
        """Rotate proxy IP using the rotation URL. Returns True if successful."""
        try:
            print("\nStarting proxy rotation...")
            await browser.create_new_tab(self.config.proxy_rotation_url)
            await browser.wait_for_page_load(timeout=10000)
            
            # Check if we hit the 1-minute cooldown
            page_content = await browser.page.content()
            if '"success":0' in page_content and "rotate IP every 1 minutes" in page_content:
                print("\nHit 1-minute cooldown. Waiting...")
                await asyncio.sleep(65)  # Wait 65 seconds to be safe
                # Refresh the page
                await browser.page.reload()
                await browser.wait_for_page_load(timeout=10000)
            
            # Initial wait for proxy rotation to start
            await asyncio.sleep(5)
            
            # Get initial IP
            old_ip = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.ipify.org?format=json") as response:
                        if response.ok:
                            data = await response.json()
                            old_ip = data.get('ip')
                            print(f"Current IP: {old_ip}")
            except Exception:
                print("Could not get initial IP")
            
            # Wait for up to 2 minutes (120 seconds) for IP rotation
            max_retries = 24  # 24 * 5 seconds = 120 seconds
            retry_count = 0
            rotation_success = False
            
            while retry_count < max_retries:
                try:
                    # Check page content for cooldown message
                    page_content = await browser.page.content()
                    if '"success":0' in page_content and "rotate IP every 1 minutes" in page_content:
                        print(f"\nCooldown active, waiting... (Attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(5)
                        await browser.page.reload()
                        continue

                    # Try to check current IP
                    async with aiohttp.ClientSession() as session:
                        async with session.get("https://api.ipify.org?format=json") as response:
                            if response.ok:
                                data = await response.json()
                                new_ip = data.get('ip')
                                if new_ip and new_ip != old_ip:
                                    print(f"\nProxy rotation successful!")
                                    print(f"Old IP: {old_ip}")
                                    print(f"New IP: {new_ip}")
                                    rotation_success = True
                                    
                                    # Close proxy rotation tab
                                    current_tabs = await browser.get_tabs_info()
                                    for tab in current_tabs:
                                        if tab.url == self.config.proxy_rotation_url:
                                            await browser.switch_to_tab(tab.page_id)
                                            await browser.close_current_tab()
                                    
                                    # Wait for connection stability
                                    await asyncio.sleep(10)
                                    return True
                except Exception as e:
                    print(f"Error checking IP: {str(e)}")
                
                print(f"Proxy rotation attempt {retry_count + 1}/{max_retries}: Waiting for new IP...")
                retry_count += 1
                await asyncio.sleep(5)
            
            print("\nProxy rotation failed: Timeout reached")
            return False
            
        except Exception as e:
            print(f"\nProxy rotation failed: {str(e)}")
            return False

    async def mimic_human_behavior(self, browser: DolphinBrowser):
        """Mimic realistic human reading behavior"""
        page = browser.page
        
        # Random session duration between min and max
        session_duration = random.randint(
            self.config.min_session_time,
            self.config.max_session_time
        )
        start_time = time.time()
        
        print(f"\nStarting reading session for {session_duration} seconds...")
        
        while time.time() - start_time < session_duration:
            try:
                # Random reading patterns
                actions = [
                    # Slow scroll
                    lambda: page.evaluate('window.scrollBy(0, 100);'),
                    # Medium scroll
                    lambda: page.evaluate('window.scrollBy(0, 300);'),
                    # Fast scroll
                    lambda: page.evaluate('window.scrollBy(0, 600);'),
                    # Scroll up a bit (like re-reading)
                    lambda: page.evaluate('window.scrollBy(0, -200);'),
                    # Pause (like reading)
                    lambda: asyncio.sleep(random.uniform(3, 8)),
                    # Mouse movement
                    lambda: page.mouse.move(
                        random.randint(100, 800),
                        random.randint(100, 600),
                        steps=random.randint(5, 10)
                    )
                ]
                
                # Randomly select and perform an action
                action = random.choice(actions)
                await action()
                
                # Random delay between actions
                await asyncio.sleep(random.uniform(1, 4))
                
                # Occasionally check time remaining
                time_left = session_duration - (time.time() - start_time)
                if time_left > 0:
                    print(f"Reading session: {int(time_left)} seconds remaining...")
                
            except Exception as e:
                print(f"Error during human behavior simulation: {str(e)}")
                break
        
        print("\nReading session completed")

    async def interact_with_landing_page(self, browser: DolphinBrowser):
        """Interact with the landing page naturally before clicking the ad link"""
        page = browser.page
        
        print("\nInteracting with landing page...")
        
        # Random initial wait
        await asyncio.sleep(random.uniform(2, 5))
        
        # Scroll around naturally
        scroll_positions = [300, 500, 200, 400]
        for scroll in scroll_positions:
            await page.evaluate(f'window.scrollBy(0, {scroll});')
            await asyncio.sleep(random.uniform(1, 3))
        
        # Move mouse around naturally before clicking
        for _ in range(3):
            await page.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600),
                steps=random.randint(5, 10)
            )
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Find and click the "CLICK HERE" button
        try:
            click_here_button = await page.wait_for_selector('text="CLICK HERE"', timeout=5000)
            if click_here_button:
                # Move to button naturally
                await click_here_button.hover()
                await asyncio.sleep(random.uniform(0.5, 1.5))
                # Click the button
                await click_here_button.click()
                print("Clicked 'CLICK HERE' button")
                
                # Wait for new tab to open
                await asyncio.sleep(5)
                return True
        except Exception as e:
            print(f"Error clicking 'CLICK HERE' button: {str(e)}")
            return False

    async def interact_with_ad_page(self, browser: DolphinBrowser):
        """Interact naturally with the ad page"""
        try:
            # Switch to the newly opened tab
            tabs = await browser.get_tabs_info()
            if len(tabs) > 1:
                await browser.switch_to_tab(-1)  # Switch to last tab
            
            page = browser.page
            
            # Random interaction duration
            interaction_time = random.randint(
                self.config.min_ad_interaction_time,
                self.config.max_ad_interaction_time
            )
            start_time = time.time()
            
            print(f"\nInteracting with ad page for {interaction_time} seconds...")
            
            while time.time() - start_time < interaction_time:
                # Mix of different natural interactions
                actions = [
                    # Slow scroll
                    lambda: page.evaluate('window.scrollBy(0, 100);'),
                    # Medium scroll
                    lambda: page.evaluate('window.scrollBy(0, 300);'),
                    # Scroll up (like re-reading)
                    lambda: page.evaluate('window.scrollBy(0, -150);'),
                    # Mouse movement
                    lambda: page.mouse.move(
                        random.randint(100, 800),
                        random.randint(100, 600),
                        steps=random.randint(5, 10)
                    ),
                    # Look for and interact with ad elements
                    lambda: self.find_and_interact_with_ads(page)
                ]
                
                action = random.choice(actions)
                await action()
                await asyncio.sleep(random.uniform(2, 5))
                
                time_left = interaction_time - (time.time() - start_time)
                if time_left > 0:
                    print(f"Ad interaction: {int(time_left)} seconds remaining...")
            
            print("\nAd interaction completed")
            
        except Exception as e:
            print(f"Error during ad interaction: {str(e)}")

    async def find_and_interact_with_ads(self, page):
        """Find and interact with ad elements naturally"""
        try:
            # Common ad selectors
            ad_selectors = [
                'iframe[id*="ad"]',
                'div[id*="ad"]',
                'a[href*="ad"]',
                'div[class*="ad"]',
                'iframe[src*="ad"]'
            ]
            
            for selector in ad_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        # Move to ad naturally
                        await element.hover()
                        await asyncio.sleep(random.uniform(1, 3))
                        
                        # Sometimes click the ad
                        if random.random() < 0.3:  # 30% chance to click
                            await element.click()
                            print("Interacted with an ad element")
                            await asyncio.sleep(random.uniform(2, 4))
                            
                            # If new tab opened, close it after a delay
                            tabs = await browser.get_tabs_info()
                            if len(tabs) > 2:  # Original + Ad page + New tab
                                await asyncio.sleep(random.uniform(3, 7))
                                await browser.close_current_tab()
                                await browser.switch_to_tab(-1)  # Back to ad page
        
        except Exception as e:
            print(f"Error interacting with ads: {str(e)}")

async def main():
    try:
        # Initialize automation
        automation = AdsterraAutomation()
        browser = None

        # Initialize Mistral AI model
        llm = ChatMistralAI(
            model="pixtral-large-latest",
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            temperature=0.1,
        )

        # Initialize controller and browser
        controller = Controller(keep_open=True)
        browser = DolphinBrowser(keep_open=True)
        
        # Connect to Dolphin profile
        profile_id = os.getenv("DOLPHIN_PROFILE_ID")
        await browser.connect(profile_id)
        controller.set_browser(browser)
        
        # Rotate proxy and verify success
        proxy_rotation_success = await automation.rotate_proxy(browser)
        
        if not proxy_rotation_success:
            print("\nAborting due to proxy rotation failure")
            return
        
        # Navigate to landing page
        print(f"\nNavigating to landing page...")
        await browser.create_new_tab(automation.config.landing_url)
        await browser.wait_for_page_load(timeout=30000)
        
        # Interact with landing page and click through to ad
        if await automation.interact_with_landing_page(browser):
            # Interact with the ad page
            await automation.interact_with_ad_page(browser)
        
        print("\nClosing all tabs and cleaning up...")

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        if browser:
            try:
                # Close all tabs
                current_tabs = await browser.get_tabs_info()
                for tab in current_tabs:
                    await browser.switch_to_tab(tab.page_id)
                    await browser.close_current_tab()
                
                # Force close browser
                await browser.close(force=True)
                print("\nBrowser closed successfully")
            except Exception as e:
                print(f"\nError during cleanup: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 