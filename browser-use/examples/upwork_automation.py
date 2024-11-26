import os
import asyncio
import random
import time
from typing import Optional, List
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent, Controller, DolphinBrowser
from pydantic import BaseModel

# Load environment variables
load_dotenv()

class JobDetails(BaseModel):
    title: str
    description: str
    budget: Optional[str]
    skills: List[str]

class UpworkConfig(BaseModel):
    keywords: List[str] = []  # Will be populated from env
    min_session_time: int = 30
    max_session_time: int = 120
    max_proposals: int = 5

    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        # Get keywords and properly handle commas and spaces
        keywords_str = os.getenv("UPWORK_KEYWORDS", "")
        if not keywords_str:
            raise ValueError("UPWORK_KEYWORDS not found in environment variables")
            
        # Split by comma and clean up each keyword
        keywords = [
            keyword.strip()
            for keyword in keywords_str.split(",")
            if keyword.strip()  # Only keep non-empty keywords
        ]
        
        if not keywords:
            raise ValueError("No valid keywords found in UPWORK_KEYWORDS")
            
        print(f"\nLoaded keywords from env: {keywords}")
        
        # Get other settings
        max_proposals = int(os.getenv("UPWORK_MAX_PROPOSALS", "5"))
        
        return cls(
            keywords=keywords,
            max_proposals=max_proposals
        )

async def check_login_status(browser: DolphinBrowser) -> bool:
    """Check if already logged into Upwork"""
    try:
        print("\nChecking Upwork login status...")
        page = browser.page
        
        # Go to Upwork homepage
        await page.goto("https://www.upwork.com/nx/jobs/search/", timeout=30000)
        await browser.wait_for_page_load()
        await asyncio.sleep(5)  # Wait for any dynamic content
        
        # Check if we're redirected to login page
        if "login" in page.url:
            print("Not logged into Upwork")
            return False
            
        # Check for login indicators
        login_indicators = [
            '[data-test="nav-user-dropdown"]',
            '.nav-user-dropdown',
            '.up-header',
            '.navbar-logged-in',
            'a[href*="logout"]',
            'button[aria-label="User Menu"]',
            '.nav-d-none'  # Additional Upwork-specific indicator
        ]
        
        for selector in login_indicators:
            try:
                element = await page.wait_for_selector(selector, timeout=5000)
                if element:
                    print("Already logged into Upwork")
                    return True
            except:
                continue
        
        print("Not logged into Upwork")
        return False
        
    except Exception as e:
        print(f"Error checking login status: {str(e)}")
        return False

async def apply_to_job(browser: DolphinBrowser, agent: Agent) -> bool:
    """Apply to a job by finding and clicking the apply button"""
    try:
        # Wait for page load
        await asyncio.sleep(5)
        
        # Try different selectors for the apply button
        apply_button_selectors = [
            'button[data-test="apply-button"]',
            'button:has-text("Apply Now")',
            'button:has-text("Submit a Proposal")',
            '[data-test="apply-button"]',
            '.up-btn-primary:has-text("Apply")',
            'a:has-text("Submit a Proposal")',
            'button.up-btn.up-btn-primary:has-text("Apply")',
            '[data-qa="apply-button"]'
        ]
        
        for selector in apply_button_selectors:
            try:
                # Wait for button to be visible
                apply_button = await browser.page.wait_for_selector(selector, timeout=5000)
                if apply_button and await apply_button.is_visible():
                    # Scroll button into view
                    await apply_button.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    
                    # Click the button
                    await apply_button.click()
                    print("Clicked apply button")
                    await asyncio.sleep(3)
                    return True
            except:
                continue
                
        print("Could not find apply button")
        return False
        
    except Exception as e:
        print(f"Error applying to job: {str(e)}")
        return False

async def fill_proposal(browser: DolphinBrowser, agent: Agent) -> bool:
    """Fill in the proposal form"""
    try:
        # Wait for form to load
        await asyncio.sleep(5)
        
        # Try different selectors for cover letter field
        cover_letter_selectors = [
            'div[data-test="cover-letter"] div[contenteditable="true"]',
            'textarea[aria-label="Cover Letter"]',
            'div[role="textbox"]',
            '[data-test="cover-letter-input"]',
            '.up-textarea',
            'div.public-DraftEditor-content',
            '[data-qa="cover-letter-input"]'
        ]
        
        cover_letter = """Dear Hiring Manager,

I am writing to express my interest in the dubbing job you have posted. With my extensive experience in voice acting and dubbing, I am confident in my ability to deliver high-quality work that meets your expectations.

I have a professional and engaging tone, and I am familiar with corporate narration and marketing content. I am also fluent in English and have experience working with various dialects.

I am excited about the opportunity to contribute to your project and would be grateful for the chance to discuss how my background and skills would make me a strong fit for your needs.

Thank you for considering my application.

Best regards,
{name}""".format(name=os.getenv("YOUR_NAME", "[Your Name]"))

        # Try to find and fill cover letter field
        cover_letter_filled = False
        for selector in cover_letter_selectors:
            try:
                field = await browser.page.wait_for_selector(selector, timeout=5000)
                if field and await field.is_visible():
                    await field.click()
                    await asyncio.sleep(1)
                    await field.fill(cover_letter)
                    print("Filled cover letter")
                    await asyncio.sleep(2)
                    cover_letter_filled = True
                    break
            except:
                continue

        if not cover_letter_filled:
            print("Could not find cover letter field")
            return False

        # Set hourly rate if required
        try:
            rate_selectors = [
                'input[data-test="hourly-rate"]',
                'input[type="number"]',
                '[data-qa="hourly-rate-input"]'
            ]
            
            for selector in rate_selectors:
                rate_input = await browser.page.wait_for_selector(selector, timeout=5000)
                if rate_input and await rate_input.is_visible():
                    await rate_input.fill(str(os.getenv("UPWORK_MIN_HOURLY_RATE", "50")))
                    print("Set hourly rate")
                    await asyncio.sleep(1)
                    break
        except:
            pass

        # Submit proposal if not in dry run mode
        if not os.getenv("DRY_RUN", "true").lower() == "true":
            submit_selectors = [
                'button[data-test="submit-proposal"]',
                'button:has-text("Submit Proposal")',
                '[data-test="submit-button"]',
                '.up-btn-primary:has-text("Submit")',
                '[data-qa="submit-proposal-button"]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = await browser.page.wait_for_selector(selector, timeout=5000)
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                        print("Submitted proposal")
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
                    
            print("Could not find submit button")
            return False
            
        else:
            print("Dry run mode - skipping submission")
            return True

    except Exception as e:
        print(f"Error filling proposal: {str(e)}")
        return False

async def search_jobs(browser: DolphinBrowser, keyword: str) -> List[str]:
    """Search for jobs and return list of job URLs"""
    try:
        # First navigate to Upwork homepage
        await browser.page.goto("https://www.upwork.com")
        await browser.wait_for_page_load()
        await asyncio.sleep(3)

        # Click on Find Work or Jobs link
        find_work_selectors = [
            'a[href="/nx/find-work/"]',
            'a:has-text("Find Work")',
            'a:has-text("Jobs")',
            '[data-test="find-work-link"]'
        ]
        
        for selector in find_work_selectors:
            try:
                find_work_link = await browser.page.wait_for_selector(selector, timeout=5000)
                if find_work_link:
                    await find_work_link.click()
                    print("Clicked Find Work link")
                    await asyncio.sleep(3)
                    break
            except:
                continue

        # Now navigate to search page with encoded keyword
        encoded_keyword = keyword.replace(" ", "%20")
        search_url = f"https://www.upwork.com/nx/jobs/search/?q={encoded_keyword}&sort=recency"
        await browser.page.goto(search_url)
        await browser.wait_for_page_load()
        await asyncio.sleep(5)  # Wait for dynamic content

        # Wait for job listings with multiple possible selectors
        job_list_selectors = [
            'section[data-test="job-tile"]',
            '.job-tile',
            '[data-test="job-tile-list"]',
            '.up-card-section',
            'div[data-test="job-tile"]'
        ]
        
        job_list_found = False
        for selector in job_list_selectors:
            try:
                await browser.page.wait_for_selector(selector, timeout=10000)
                job_list_found = True
                print(f"Found job listings with selector: {selector}")
                break
            except:
                continue
                
        if not job_list_found:
            print(f"No job listings found for keyword: {keyword}")
            return []

        # Get all job links with multiple possible selectors
        job_link_selectors = [
            'h4[data-test="job-title"] a',
            '.job-title a',
            'a[data-test="job-title-link"]',
            '.up-n-link',
            'a[href*="/jobs/"]'
        ]
        
        urls = []
        max_jobs = int(os.getenv("UPWORK_MAX_PROPOSALS", "5"))
        
        for selector in job_link_selectors:
            try:
                job_links = await browser.page.query_selector_all(selector)
                for link in job_links[:max_jobs]:
                    url = await link.get_attribute('href')
                    if url:
                        # Filter out non-job URLs
                        if '/jobs/' in url and 'search' not in url:
                            if not url.startswith('http'):
                                url = f"https://www.upwork.com{url}"
                            if url not in urls:  # Avoid duplicates
                                urls.append(url)
                                print(f"Found job: {url}")
                if urls:
                    break
            except:
                continue

        return urls

    except Exception as e:
        print(f"Error searching jobs: {str(e)}")
        return []

async def main():
    browser = None
    try:
        # Initialize automation with config from env
        config = UpworkConfig.from_env()
        print(f"\nUsing search keywords: {config.keywords}")
        
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
        if not profile_id:
            print("Error: DOLPHIN_PROFILE_ID not found in environment variables")
            return
            
        await browser.connect(profile_id)
        controller.set_browser(browser)
        
        # Initialize agent for interactions
        agent = Agent(
            task="Apply to jobs on Upwork",
            llm=llm,
            controller=controller,
            use_vision=True,
            max_failures=5,
            retry_delay=3,
        )
        
        # Check if already logged in
        is_logged_in = await check_login_status(browser)
        
        # Only perform login if not already logged in
        if not is_logged_in:
            # Initialize login agent
            login_agent = Agent(
                task=f"""
                Login to Upwork with these credentials:
                Username: {os.getenv("UPWORK_USERNAME")}
                Password: {os.getenv("UPWORK_PASSWORD")}
                
                Steps:
                1. Go to https://www.upwork.com/ab/account-security/login
                2. Wait for page to load completely
                3. Fill in username field with the username
                4. Click Continue or Submit button
                5. Wait for password field to appear
                6. Fill in password field with the password
                7. Click Login button
                8. Wait for successful login
                """,
                llm=llm,
                controller=controller,
                use_vision=True,
                max_failures=5,
                retry_delay=3,
            )

            # Attempt login
            login_result = await login_agent.run()
            print("\nLogin Result:", login_result)

            # Verify login was successful
            is_logged_in = await check_login_status(browser)
            if not is_logged_in:
                print("Failed to login to Upwork. Aborting...")
                return

        # Search and apply for each keyword
        for keyword in config.keywords:
            print(f"\nSearching for: {keyword}")
            
            # Get job URLs
            job_urls = await search_jobs(browser, keyword)
            
            for url in job_urls:
                print(f"\nProcessing job: {url}")
                
                # Navigate to job
                await browser.page.goto(url)
                await browser.wait_for_page_load()
                await asyncio.sleep(3)
                
                # Apply to job
                if await apply_to_job(browser, agent):
                    # Fill proposal
                    if await fill_proposal(browser, agent):
                        print("Successfully processed job")
                    else:
                        print("Failed to fill proposal")
                else:
                    print("Failed to apply to job")
                
                # Random delay between jobs
                delay = random.uniform(
                    config.min_session_time,
                    config.max_session_time
                )
                print(f"\nWaiting {int(delay)} seconds before next job...")
                await asyncio.sleep(delay)

        print("\nJob search and proposal submission completed!")

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        if browser:
            try:
                await browser.close(force=True)
                print("\nBrowser closed successfully")
            except Exception as e:
                print(f"\nError during cleanup: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 