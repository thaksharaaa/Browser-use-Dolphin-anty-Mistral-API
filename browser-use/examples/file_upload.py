import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent, Controller, DolphinBrowser
from browser_use.browser.service import Browser

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

        # Initialize controller and browser
        controller = Controller(keep_open=True)
        browser = DolphinBrowser(keep_open=True)
        
        # Connect to Dolphin profile
        profile_id = os.getenv("DOLPHIN_PROFILE_ID")
        await browser.connect(profile_id)
        controller.set_browser(browser)

        # Define upload sites
        sites = [
            'https://practice.expandtesting.com/upload',
            'https://ps.uci.edu/~franklin/doc/file_upload.html',
        ]

        # Initialize the browser agent
        agent = Agent(
            task=f'go to {" ".join(sites)} each in new tabs and Upload my file then submit',
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
        if 'browser' in locals():
            await browser.close(force=True)

if __name__ == "__main__":
    asyncio.run(main())
