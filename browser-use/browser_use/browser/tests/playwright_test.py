import time

import pytest
from playwright.async_api import Page

from browser_use.dom.service import DomService


@pytest.fixture(scope='session')
def browser_type_launch_args():
	return {'headless': False}


async def test_has_title(page: Page):
	dom_service = DomService(page)

	await page.goto('https://www.immobilienscout24.de')
	await page.wait_for_timeout(2000)

	# Get all DOM content including all shadow roots recursively
	start_time = time.time()
	# wait for the page to load
	await page.wait_for_load_state('load')
	full_content = await dom_service._get_html_content()
	# full_content = page.evaluate("""() => {
	# 	function getAllContent(root) {
	# 		let content = '';
	# 		// Get all elements in the current root
	# 		const elements = root.querySelectorAll('*');

	# 		elements.forEach(element => {
	# 			// Add the element's outer HTML
	# 			content += element.outerHTML;
	# 			// If element has shadow root, recursively get its content
	# 			if (element.shadowRoot) {
	# 				content += `\\n<!-- Shadow DOM for ${element.tagName} -->\\n`;
	# 				content += getAllContent(element.shadowRoot);
	# 				content += `\\n<!-- End Shadow DOM for ${element.tagName} -->\\n`;
	# 			}
	# 		});
	# 		return content;
	# 	}
	# 	return getAllContent(document);
	# }""")
	end_time = time.time()

	print(full_content)
	print(f'Time taken to get DOM content: {end_time - start_time:.2f} seconds')

	elements = dom_service._process_content(full_content)

	print(elements)

	input('Press Enter to continue...')
