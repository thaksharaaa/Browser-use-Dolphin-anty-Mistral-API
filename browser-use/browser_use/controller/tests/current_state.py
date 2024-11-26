import pytest

from browser_use.agent.views import ActionModel
from browser_use.controller.service import Controller


def test_get_current_state():
	# Initialize controller
	controller = Controller()

	# Go to a test URL
	# controller.act(ActionModel(name='go_to_url', url='https://www.example.com'))

	# Get current state without screenshot
	state = controller.browser.get_state(use_vision=True)

	input('Press Enter to continue...')
