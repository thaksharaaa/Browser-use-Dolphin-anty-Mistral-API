import pytest
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from browser_use.agent.service import Agent
from browser_use.controller.service import Controller


@pytest.fixture
def llm():
	"""Initialize language model for testing"""

	# return ChatAnthropic(model_name='claude-3-5-sonnet-20240620', timeout=25, stop=None)
	return ChatOpenAI(model='gpt-4o')
	# return ChatOpenAI(model='gpt-4o-mini')


@pytest.fixture
async def agent_with_controller():
	"""Create agent with controller for testing"""
	controller = Controller(keep_open=False)
	print('init controller')
	try:
		yield controller
	finally:
		if controller.browser:
			await controller.browser.close(force=True)


# @pytest.mark.asyncio
async def test_ecommerce_interaction(llm, agent_with_controller):
	"""Test complex ecommerce interaction sequence"""
	agent = Agent(
		task="Go to amazon.com, search for 'laptop', filter by 4+ stars, and find the price of the first result",
		llm=llm,
		controller=agent_with_controller,
		save_conversation_path='tmp/test_ecommerce_interaction/conversation',
	)

	history = await agent.run(max_steps=20)

	# Verify sequence of actions
	action_sequence = []
	for h in history:
		action = getattr(h.model_output, 'action', None)
		if action and (getattr(action, 'go_to_url', None) or getattr(action, 'open_tab', None)):
			action_sequence.append('navigate')
		elif action and getattr(action, 'input_text', None):
			action_sequence.append('input')
			# Check that the input is 'laptop'
			inp = action.input_text.text.lower()
			if inp == 'laptop':
				action_sequence.append('input_exact_correct')
			elif 'laptop' in inp:
				action_sequence.append('correct_in_input')
			else:
				action_sequence.append('incorrect_input')

		elif action and getattr(action, 'click_element', None):
			action_sequence.append('click')

		if action is None:
			print(h.result)
			print(h.model_output)

	# Verify essential steps were performed
	assert 'navigate' in action_sequence  # Navigated to Amazon
	assert 'input' in action_sequence  # Entered search term
	assert 'click' in action_sequence  # Clicked search/filter
	assert 'input_exact_correct' in action_sequence or 'correct_in_input' in action_sequence


# @pytest.mark.asyncio
async def test_error_recovery(llm, agent_with_controller):
	"""Test agent's ability to recover from errors"""
	agent = Agent(
		task='Navigate to nonexistent-site.com and then recover by going to google.com',
		llm=llm,
		controller=agent_with_controller,
	)

	history = await agent.run(max_steps=10)

	recovery_action = next(
		(
			h
			for h in history
			if h.model_output
			and getattr(h.model_output, 'action', None)
			and getattr(h.model_output.action, 'go_to_url', None)
			and getattr(h.model_output.action.go_to_url, 'url', '').endswith('google.com')  # type: ignore -> pretty weird way to do this
		),
		None,
	)
	assert recovery_action is not None


# @pytest.mark.asyncio
async def test_find_contact_email(llm, agent_with_controller):
	"""Test agent's ability to find contact email on a website"""
	agent = Agent(
		task='Go to https://browser-use.com/ and find out the contact email',
		llm=llm,
		controller=agent_with_controller,
	)

	history = await agent.run(max_steps=10)

	# Verify the agent found the contact email
	email_action = next(
		(
			h
			for h in history
			if h.result.extracted_content and 'info@browser-use.com' in h.result.extracted_content
		),
		None,
	)
	assert email_action is not None


# @pytest.mark.asyncio
async def test_agent_finds_installation_command(llm, agent_with_controller):
	"""Test agent's ability to find the pip installation command for browser-use on the web"""
	agent = Agent(
		task='Find the pip installation command for the browser-use repo',
		llm=llm,
		controller=agent_with_controller,
	)

	history = await agent.run(max_steps=10)

	# Verify the agent found the correct installation command
	install_command_action = next(
		(
			h
			for h in history
			if h.result.extracted_content
			and 'pip install browser-use' in h.result.extracted_content
		),
		None,
	)
	assert install_command_action is not None


class CaptchaTest(BaseModel):
	name: str
	url: str
	success_text: str
	additional_text: str | None = None


# pytest tests/test_agent_actions.py -v -k "test_captcha_solver" --capture=no --log-cli-level=INFO
@pytest.mark.asyncio
@pytest.mark.parametrize(
	'captcha',
	[
		# good test for num_clicks
		CaptchaTest(
			name='Rotate Captcha',
			url='https://2captcha.com/demo/rotatecaptcha',
			success_text='Captcha is passed successfully',
			additional_text='Use num_clicks with number to click multiple times at once in same direction. click done when image is exact correct position.',
		),
		CaptchaTest(
			name='Text Captcha',
			url='https://2captcha.com/demo/text',
			success_text='Captcha is passed successfully!',
		),
		CaptchaTest(
			name='Basic Captcha',
			url='https://captcha.com/demos/features/captcha-demo.aspx',
			success_text='Correct!',
		),
		CaptchaTest(
			name='MT Captcha',
			url='https://2captcha.com/demo/mtcaptcha',
			success_text='Verified Successfully',
			additional_text='Stop when you solved it successfully.',
		),
	],
)
async def test_captcha_solver(llm, agent_with_controller, captcha: CaptchaTest):
	"""Test agent's ability to solve different types of captchas"""
	agent = Agent(
		task=f'Go to {captcha.url} and solve the captcha. {captcha.additional_text}',
		llm=llm,
		controller=agent_with_controller,
	)
	from browser_use.agent.views import AgentHistoryList

	history = await agent.run(max_steps=10)

	# Verify the agent solved the captcha
	solved = False
	for h in history:
		last = h.state.items
		if any(captcha.success_text in item.text for item in last):
			solved = True
			break
	assert solved, f'Failed to solve {captcha.name}'


# python -m pytest tests/test_agent_actions.py -v --capture=no


# pytest tests/test_agent_actions.py -v -k "test_captcha_solver" --capture=no --log-cli-level=INFO
