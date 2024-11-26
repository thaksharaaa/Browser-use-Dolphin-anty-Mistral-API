import logging

from main_content_extractor import MainContentExtractor

from browser_use.agent.views import ActionModel, ActionResult
from browser_use.browser.dolphin_service import DolphinBrowser
from browser_use.controller.registry.service import Registry
from browser_use.controller.views import (
	ClickElementAction,
	DoneAction,
	ExtractPageContentAction,
	GoToUrlAction,
	InputTextAction,
	OpenTabAction,
	ScrollAction,
	SearchGoogleAction,
	SwitchTabAction,
)
from browser_use.utils import time_execution_sync

logger = logging.getLogger(__name__)


class Controller:
	def __init__(self, headless: bool = False, keep_open: bool = False):
		self.browser = None
		self.registry = Registry()
		self._register_default_actions()

	def set_browser(self, browser: DolphinBrowser):
		"""Set the browser instance"""
		self.browser = browser

	def _register_default_actions(self):
		"""Register all default browser actions"""

		# Basic Navigation Actions
		@self.registry.action(
			'Search Google', param_model=SearchGoogleAction, requires_browser=True
		)
		async def search_google(params: SearchGoogleAction, browser: DolphinBrowser):
			page = browser.page
			await page.goto(f'https://www.google.com/search?q={params.query}')
			await browser.wait_for_page_load()

		@self.registry.action('Navigate to URL', param_model=GoToUrlAction, requires_browser=True)
		async def go_to_url(params: GoToUrlAction, browser: DolphinBrowser):
			page = browser.page
			await page.goto(params.url)
			await browser.wait_for_page_load()

		@self.registry.action('Go back', requires_browser=True)
		async def go_back(browser: DolphinBrowser):
			page = browser.page
			await page.go_back()
			await browser.wait_for_page_load()

		# Element Interaction Actions
		@self.registry.action(
			'Click element', param_model=ClickElementAction, requires_browser=True
		)
		async def click_element(params: ClickElementAction, browser: DolphinBrowser):
			session = await browser.get_session()
			state = session.cached_state

			if params.index not in state.selector_map:
				print(state.selector_map)
				raise Exception(
					f'Element with index {params.index} does not exist - retry or use alternative actions'
				)

			xpath = state.selector_map[params.index]
			initial_pages = len(session.context.pages)

			msg = None

			for _ in range(params.num_clicks):
				try:
					await browser._click_element_by_xpath(xpath)
					msg = f'🖱️  Clicked element {params.index}: {xpath}'
					if params.num_clicks > 1:
						msg += f' ({_ + 1}/{params.num_clicks} clicks)'
				except Exception as e:
					logger.warning(f'Element no longer available after {_ + 1} clicks: {str(e)}')
					break

			if len(session.context.pages) > initial_pages:
				await browser.switch_to_tab(-1)

			return ActionResult(extracted_content=f'{msg}')

		@self.registry.action('Input text', param_model=InputTextAction, requires_browser=True)
		async def input_text(params: InputTextAction, browser: DolphinBrowser):
			session = await browser.get_session()
			state = session.cached_state

			if params.index not in state.selector_map:
					raise Exception(
					f'Element index {params.index} does not exist - retry or use alternative actions'
				)

			xpath = state.selector_map[params.index]
			await browser._input_text_by_xpath(xpath, params.text)
			msg = f'⌨️  Input "{params.text}" into {params.index}: {xpath}'
			return ActionResult(extracted_content=msg)

		# Tab Management Actions
		@self.registry.action('Switch tab', param_model=SwitchTabAction, requires_browser=True)
		async def switch_tab(params: SwitchTabAction, browser: DolphinBrowser):
			await browser.switch_to_tab(params.page_id)
			# Wait for tab to be ready
			await browser.wait_for_page_load()

		@self.registry.action('Open new tab', param_model=OpenTabAction, requires_browser=True)
		async def open_tab(params: OpenTabAction, browser: DolphinBrowser):
			await browser.create_new_tab(params.url)

		# Content Actions
		@self.registry.action(
			'Extract page content to get the text or markdown ',
			param_model=ExtractPageContentAction,
			requires_browser=True,
		)
		async def extract_content(params: ExtractPageContentAction, browser: DolphinBrowser):
			page = browser.page

			content = MainContentExtractor.extract(  # type: ignore
				html=await page.content(),
				output_format=params.value,
			)
			return ActionResult(extracted_content=content)

		@self.registry.action('Complete task', param_model=DoneAction, requires_browser=True)
		async def done(params: DoneAction, browser: DolphinBrowser):
			session = await browser.get_session()
			state = session.cached_state
			return ActionResult(is_done=True, extracted_content=params.text)

		@self.registry.action(
			'Scroll down the page by pixel amount - if no amount is specified, scroll down one page',
			param_model=ScrollAction,
			requires_browser=True,
		)
		async def scroll_down(params: ScrollAction, browser: DolphinBrowser):
			page = browser.page
			if params.amount is not None:
				await page.evaluate(f'window.scrollBy(0, {params.amount});')
			else:
				await page.keyboard.press('PageDown')

		# scroll up
		@self.registry.action(
			'Scroll up the page by pixel amount',
			param_model=ScrollAction,
			requires_browser=True,
		)
		async def scroll_up(params: ScrollAction, browser: DolphinBrowser):
			page = browser.page
			if params.amount is not None:
				await page.evaluate(f'window.scrollBy(0, -{params.amount});')
			else:
					await page.keyboard.press('PageUp')

	def action(self, description: str, **kwargs):
		"""Decorator for registering custom actions

		@param description: Describe the LLM what the function does (better description == better function calling)
		"""
		return self.registry.action(description, **kwargs)

	@time_execution_sync('--act')
	async def act(self, action: ActionModel) -> ActionResult:
		"""Execute an action"""
		try:
			for action_name, params in action.model_dump(exclude_unset=True).items():
				if params is not None:
					try:
						result = await self.registry.execute_action(
							action_name, params, browser=self.browser
						)
						
						# Handle different result types
						if result is None:
							return ActionResult()
						elif isinstance(result, str):
							return ActionResult(extracted_content=result)
						elif isinstance(result, ActionResult):
							return result
						elif hasattr(result, 'model_dump_json'):
							return ActionResult(extracted_content=result.model_dump_json())
						else:
							return ActionResult(extracted_content=str(result))
							
					except Exception as e:
						logger.error(f"Action execution error: {str(e)}")
						return ActionResult(error=str(e))
						
			return ActionResult()
			
		except Exception as e:
			logger.error(f"Controller action error: {str(e)}")
			return ActionResult(error=str(e))
