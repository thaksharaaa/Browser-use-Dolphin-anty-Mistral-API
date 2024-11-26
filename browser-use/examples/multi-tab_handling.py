"""
Simple try of the agent.

@dev You need to add OPENAI_API_KEY to your environment variables.
"""

import os
import asyncio
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent, Controller, DolphinBrowser

# Load environment variables
load_dotenv()

async def main():
    try:
        # Initialize Mistral AI model
        llm = ChatMistralAI(
            model="pixtral-large-latest",
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            temperature=0.1,
        )

        # Initialize controller first
        controller = Controller(keep_open=True)

        # Initialize and connect Dolphin browser
        browser = DolphinBrowser(keep_open=True)
        
        # Authenticate and connect to profile
        profile_id = os.getenv("DOLPHIN_PROFILE_ID")
        if not profile_id:
            # Get first available profile if none specified
            profiles = await browser.get_browser_profiles()
            if not profiles:
                raise Exception("No browser profiles found in Dolphin Anty")
            profile_id = str(profiles[0]["id"])

        # Connect to the profile
        await browser.connect(profile_id)
        
        # Set the browser in controller
        controller.set_browser(browser)

        # Initialize the browser agent with a more structured task
        agent = Agent(
            task="""
            Please follow these steps:
            1. Open a new tab and search for "elon musk" on Google
            2. Open another tab and search for "trump" on Google
            3. Open a third tab and search for "steve jobs" on Google
            4. Go back to the first tab
            5. Click on the first link in the search results
            """,
            llm=llm,
            controller=controller,
            use_vision=True,
            max_failures=10,  # Increase max failures for more retries
            retry_delay=2,    # Reduce retry delay
        )

        result = await agent.run()
        print("Final Result:", result)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e
    finally:
        if 'browser' in locals():
            try:
                await browser.close(force=True)
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
