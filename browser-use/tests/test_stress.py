import time

import pytest
from langchain_openai import ChatOpenAI

from browser_use.agent.service import Agent
from browser_use.controller.service import Controller


@pytest.fixture
def llm():
	"""Initialize the language model"""
	return ChatOpenAI(model='gpt-4o')  # Use appropriate model


@pytest.fixture
async def controller():
	"""Initialize the controller"""
	controller = Controller()
	try:
		yield controller
	finally:
		if controller.browser:
			await controller.browser.close(force=True)


# should get rate limited
@pytest.mark.asyncio
async def test_open_10_tabs_and_extract_content(llm, controller):
	"""Stress test: Open 10 tabs and extract content"""
	agent = Agent(
		task='Open new tabs with example.com, example.net, example.org. Then, extract the content from each.',
		llm=llm,
		controller=controller,
	)
	start_time = time.time()
	history = await agent.run(max_steps=50)
	end_time = time.time()

	total_time = end_time - start_time

	print(f'Total time: {total_time:.2f} seconds')
	# Check for errors
	errors = [h.result.error for h in history if h.result and h.result.error]
	assert len(errors) == 0, 'Errors occurred during the test'
	# check if 10 tabs were opened
	assert len(controller.browser.current_state.tabs) >= 3, '3 tabs were not opened'
