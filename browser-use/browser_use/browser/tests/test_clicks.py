import time

import pytest

from browser_use.browser.service import Browser
from browser_use.utils import time_execution_sync


@pytest.mark.asyncio
async def test_highlight_elements():
    browser = Browser(headless=False, keep_open=False)

    session = await browser.get_session()

    print(session)

    page = await browser.get_current_page()
    # await page.goto('https://immobilienscout24.de')
    await page.goto("https://kayak.com")

    time.sleep(3)
    # browser._click_element_by_xpath(
    # 	'/html/body/div[5]/div/div[2]/div/div/div[3]/div/div[1]/button[1]'
    # )
    # browser._click_element_by_xpath("//button[div/div[text()='Alle akzeptieren']]")

    while True:
        state = await browser.get_state()

        await time_execution_sync("highlight_selector_map_elements")(
            browser.highlight_selector_map_elements
        )(state.selector_map)

        print(state.dom_items_to_string(use_tabs=False))
        # print(state.selector_map)

        # Find and print duplicate XPaths
        xpath_counts = {}
        for selector in state.selector_map.values():
            if selector in xpath_counts:
                xpath_counts[selector] += 1
            else:
                xpath_counts[selector] = 1

        print("\nDuplicate XPaths found:")
        for xpath, count in xpath_counts.items():
            if count > 1:
                print(f"XPath: {xpath}")
                print(f"Count: {count}\n")

        print(state.selector_map.keys(), "Selector map keys")
        action = input("Select next action: ")

        await time_execution_sync("remove_highlight_elements")(
            browser.remove_highlights
        )()

        xpath = state.selector_map[int(action)]

        # check if index of selector map are the same as index of items in dom_items

        indcies = list(state.selector_map.keys())
        dom_items = state.items
        dom_indices = [item.index for item in dom_items if not item.is_text_only]
        assert (
            indcies == dom_indices
        ), "Indices of selector map and dom items do not match"

        await browser._click_element_by_xpath(xpath)
