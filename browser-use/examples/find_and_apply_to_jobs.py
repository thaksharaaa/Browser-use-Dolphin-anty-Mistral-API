"""
Find and apply to jobs.

@dev You need to add OPENAI_API_KEY to your environment variables.

Also you have to install PyPDF2: pip install PyPDF2
"""

import os
import asyncio
import csv
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel
from browser_use import Agent, Controller, DolphinBrowser
from PyPDF2 import PdfReader

# Load environment variables
load_dotenv()

class Job(BaseModel):
	title: str
	link: str
	company: str
	salary: Optional[str] = None
	location: Optional[str] = None

class Jobs(BaseModel):
	jobs: List[Job]

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

		# Initialize the browser agent
		agent = Agent(
			task="""
			Read my cv & find machine learning engineer jobs for me. 
			Save them to a file, then start applying for them in new tabs - please not via job portals like linkedin, indeed, etc. 
			If you need more information or help, ask me.
			""",
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
