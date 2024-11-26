from typing import Dict, List
from pydantic import BaseModel


class DomContentItem(BaseModel):
	index: int
	text: str
	is_text_only: bool
	depth: int


SelectorMap = dict[int, str]


class ProcessedDomContent(BaseModel):
	items: list[DomContentItem]
	selector_map: SelectorMap

	def dom_items_to_string(self, use_tabs: bool = True) -> str:
		"""Convert the processed DOM content to HTML."""
		formatted_text = ''
		for item in self.items:
			item_depth = '\t' * item.depth * 1 if use_tabs else ''
			if item.is_text_only:
				formatted_text += f'_[:]{item_depth}{item.text}\n'
			else:
				formatted_text += f'{item.index}[:]{item_depth}{item.text}\n'
		return formatted_text


class ElementState(BaseModel):
	isVisible: bool
	isTopElement: bool


class TextState(BaseModel):
	isVisible: bool


class ElementCheckResult(BaseModel):
	xpath: str
	isVisible: bool
	isTopElement: bool


class TextCheckResult(BaseModel):
	xpath: str
	isVisible: bool


class BatchCheckResults(BaseModel):
	elements: Dict[str, ElementCheckResult]
	texts: Dict[str, TextCheckResult]
