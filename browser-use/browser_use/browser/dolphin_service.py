import os
import json
import aiohttp
import logging
from typing import Optional, List
from playwright.async_api import async_playwright, Browser as PlaywrightBrowser, Page
from browser_use.browser.service import Browser
from browser_use.browser.views import BrowserState, TabInfo

logger = logging.getLogger(__name__)

class DolphinBrowser(Browser):
    def __init__(self, headless: bool = False, keep_open: bool = False):
        self.api_token = os.getenv("DOLPHIN_API_TOKEN")
        self.api_url = os.getenv("DOLPHIN_API_URL", "http://localhost:3001/v1.0")
        self.profile_id = os.getenv("DOLPHIN_PROFILE_ID")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = headless
        self.keep_open = keep_open
        self._pages: List[Page] = []
        self.session = None
        self.cached_state = None

    async def get_current_page(self) -> Page:
        """Get the current page"""
        if not self.page:
            raise Exception("No active page. Browser might not be connected.")
        return self.page

    async def create_new_tab(self, url: str | None = None) -> None:
        """Create a new tab and optionally navigate to a URL"""
        if not self.context:
            raise Exception("Browser context not initialized")
        
        # Create new page
        new_page = await self.context.new_page()
        self._pages.append(new_page)
        self.page = new_page  # Set as current page
        
        if url:
            try:
                await new_page.goto(url, wait_until="networkidle")
                await self.wait_for_page_load()
            except Exception as e:
                logger.error(f"Failed to navigate to URL {url}: {str(e)}")
                raise

    async def switch_to_tab(self, page_id: int) -> None:
        """Switch to a specific tab by its page_id"""
        if not self._pages:
            raise Exception("No tabs available")
            
        # Handle negative indices
        if page_id < 0:
            page_id = len(self._pages) + page_id
            
        if page_id >= len(self._pages) or page_id < 0:
            raise Exception(f"Tab index {page_id} out of range")
            
        self.page = self._pages[page_id]
        await self.page.bring_to_front()
        await self.wait_for_page_load()

    async def get_tabs_info(self) -> list[TabInfo]:
        """Get information about all tabs"""
        tabs_info = []
        for idx, page in enumerate(self._pages):
            tab_info = TabInfo(
                page_id=idx,
                url=page.url,
                title=await page.title()
            )
            tabs_info.append(tab_info)
        return tabs_info

    async def wait_for_page_load(self, timeout: int = 30000):
        """Wait for page to load"""
        if self.page:
            try:
                await self.page.wait_for_load_state("networkidle", timeout=timeout)
            except Exception as e:
                logger.warning(f"Wait for page load timeout: {str(e)}")

    async def get_session(self):
        """Get the current session"""
        if not self.browser:
            raise Exception("Browser not connected. Call connect() first.")
        self.session = self
        return self

    async def authenticate(self):
        """Authenticate with Dolphin Anty"""
        async with aiohttp.ClientSession() as session:
            auth_url = f"{self.api_url}/auth/login-with-token"
            auth_data = {"token": self.api_token}
            async with session.post(auth_url, json=auth_data) as response:
                if not response.ok:
                    raise Exception(f"Failed to authenticate with Dolphin Anty: {await response.text()}")
                return await response.json()

    async def get_browser_profiles(self):
        """Get list of available browser profiles"""
        # First authenticate
        await self.authenticate()
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.api_token}"}
            async with session.get(f"{self.api_url}/browser_profiles", headers=headers) as response:
                if not response.ok:
                    raise Exception(f"Failed to get browser profiles: {await response.text()}")
                data = await response.json()
                return data.get("data", [])  # Return the actual profiles array

    async def start_profile(self, profile_id: Optional[str] = None, headless: bool = False) -> dict:
        """Start a browser profile"""
        # First authenticate
        await self.authenticate()
        
        profile_id = profile_id or self.profile_id
        if not profile_id:
            raise ValueError("No profile ID provided")

        url = f"{self.api_url}/browser_profiles/{profile_id}/start"
        params = {"automation": 1}
        if headless:
            params["headless"] = 1

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if not response.ok:
                    raise Exception(f"Failed to start profile: {await response.text()}")
                return await response.json()

    async def stop_profile(self, profile_id: Optional[str] = None):
        """Stop a browser profile"""
        # First authenticate
        await self.authenticate()
        
        profile_id = profile_id or self.profile_id
        if not profile_id:
            raise ValueError("No profile ID provided")

        url = f"{self.api_url}/browser_profiles/{profile_id}/stop"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def connect(self, profile_id: Optional[str] = None):
        """Connect to a running browser profile using Playwright"""
        # First authenticate
        await self.authenticate()
        
        profile_data = await self.start_profile(profile_id)
        
        if not profile_data.get("success"):
            raise Exception(f"Failed to start profile: {profile_data}")

        automation = profile_data["automation"]
        port = automation["port"]
        ws_endpoint = automation["wsEndpoint"]
        ws_url = f"ws://127.0.0.1:{port}{ws_endpoint}"

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(ws_url)
        
        # Get the default context
        contexts = self.browser.contexts
        if not contexts:
            self.context = await self.browser.new_context()
        else:
            self.context = contexts[0]
            
        # Get or create initial page
        pages = self.context.pages
        if not pages:
            self.page = await self.context.new_page()
        else:
            self.page = pages[0]
            
        self._pages = [self.page]  # Initialize pages list with first page
        
        return self.browser

    async def close(self, force: bool = False):
        """Close the browser connection"""
        try:
            if self._pages:
                for page in self._pages:
                    try:
                        await page.close()
                    except:
                        pass
                self._pages = []
                
            if self.browser:
                await self.browser.close()
                
            if self.playwright:
                await self.playwright.stop()
                
            if force:
                await self.stop_profile()
        except Exception as e:
            logger.error(f"Error during browser cleanup: {str(e)}") 

    async def get_current_state(self) -> BrowserState:
        """Get current browser state"""
        if not self.page:
            raise Exception("No active page")
            
        # Get page content and viewport size
        content = await self.page.content()
        viewport_size = await self.page.viewport_size()
        
        # Create browser state
        state = BrowserState(
            url=self.page.url,
            content=content,
            viewport_height=viewport_size["height"] if viewport_size else 0,
            viewport_width=viewport_size["width"] if viewport_size else 0,
            tabs=await self.get_tabs_info()
        )
        
        self.cached_state = state
        return state

    def __del__(self):
        """Clean up resources"""
        # No need to handle session cleanup as we're using self as session
        pass