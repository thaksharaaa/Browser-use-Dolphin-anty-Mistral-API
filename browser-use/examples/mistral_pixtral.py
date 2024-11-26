import os
import asyncio
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from browser_use import Agent
from browser_use.controller.service import Controller

# Load environment variables
load_dotenv()

async def main():
    # Initialize the Mistral AI chat model with Pixtral Large
    llm = ChatMistralAI(
        model="pixtral-large-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.1,  # Lower temperature for more focused responses
    )

    # Initialize the browser agent with vision capabilities
    agent = Agent(
        task="Go to google.com and search for 'OpenAI'. Click on the first result and tell me what you see.",
        llm=llm,
        controller=Controller(keep_open=True),
        use_vision=True,  # Enable vision capabilities to leverage Pixtral's multimodal features
    )

    # Run the agent and get results
    result = await agent.run()
    print("Final Result:", result)

if __name__ == "__main__":
    asyncio.run(main()) 