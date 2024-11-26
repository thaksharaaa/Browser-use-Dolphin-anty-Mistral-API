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
        model = ChatMistralAI(
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

        # Initialize browser agents
        agent1 = Agent(
            task='Open 2 tabs with wikipedia articles about the history of the meta and one random wikipedia article.',
            llm=model,
            controller=controller,
            use_vision=True,
        )

        agent2 = Agent(
            task='Considering all open tabs give me the names of the wikipedia article.',
            llm=model,
            controller=controller,
            use_vision=True,
        )

        await agent1.run()
        await agent2.run()

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e
    finally:
        if 'browser' in locals():
            await browser.close(force=True)

if __name__ == "__main__":
    asyncio.run(main())
