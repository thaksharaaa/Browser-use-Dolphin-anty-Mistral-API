import os
import asyncio
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent, Controller, DolphinBrowser

# Load environment variables
load_dotenv()

async def main():
    try:
        # Initialize the Mistral AI chat model
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

        # Initialize the browser agent
        agent = Agent(
            task="Go to google.com and search for 'OpenAI'. Click on the first result and tell me what you see.",
            llm=llm,
            controller=controller,
            use_vision=True,
        )

        result = await agent.run()
        print("Final Result:", result)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e
    finally:
        if browser:
            await browser.close(force=True)

if __name__ == "__main__":
    asyncio.run(main()) 