from __future__ import annotations

import traceback
from typing import Optional, Type

from openai import RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from browser_use.browser.views import BrowserState
from browser_use.controller.registry.views import ActionModel


class TokenDetails(BaseModel):
	audio: int = 0
	cache_read: int = 0
	reasoning: int = 0


class TokenUsage(BaseModel):
	input_tokens: int
	output_tokens: int
	total_tokens: int
	input_token_details: TokenDetails = Field(default=TokenDetails())
	output_token_details: TokenDetails = Field(default=TokenDetails())

	# allow arbitrary types
	model_config = ConfigDict(arbitrary_types_allowed=True)


class Pricing(BaseModel):
	uncached_input: float  # per 1M tokens
	cached_input: float
	output: float


class ModelPricingCatalog(BaseModel):
	gpt_4o: Pricing = Field(default=Pricing(uncached_input=2.50, cached_input=1.25, output=10.00))
	gpt_4o_mini: Pricing = Field(
		default=Pricing(uncached_input=0.15, cached_input=0.075, output=0.60)
	)
	claude_3_5_sonnet: Pricing = Field(
		default=Pricing(uncached_input=3.00, cached_input=1.50, output=15.00)
	)


class ActionResult(BaseModel):
	"""Result of executing an action"""

	is_done: Optional[bool] = False
	extracted_content: Optional[str] = None
	error: Optional[str] = None


class AgentBrain(BaseModel):
	"""Current state of the agent"""

	valuation_previous_goal: str
	memory: str
	next_goal: str


class AgentOutput(BaseModel):
	"""Output model for agent

	@dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
	"""

	model_config = ConfigDict(arbitrary_types_allowed=True)

	current_state: AgentBrain
	action: ActionModel

	@staticmethod
	def type_with_custom_actions(custom_actions: Type[ActionModel]) -> Type['AgentOutput']:
		"""Extend actions with custom actions"""
		return create_model(
			'AgentOutput',
			__base__=AgentOutput,
			action=(custom_actions, Field(...)),  # Properly annotated field with no default
			__module__=AgentOutput.__module__,
		)


class AgentHistory(BaseModel):
	"""History item for agent actions"""

	model_output: AgentOutput | None
	result: ActionResult
	state: BrowserState

	model_config = ConfigDict(arbitrary_types_allowed=True, protected_namespaces=())


class AgentHistoryList(BaseModel):
	"""List of agent history items"""

	history: list[AgentHistory]

	def __str__(self) -> str:
		"""Representation of the AgentHistoryList object"""
		return f'AgentHistoryList(all_results={self.action_results()}, all_model_outputs={self.model_actions()})'

	def __repr__(self) -> str:
		"""Representation of the AgentHistoryList object"""
		return self.__str__()

	def last_action(self) -> None | dict:
		"""Last action in history"""
		if self.history and self.history[-1].model_output:
			return self.history[-1].model_output.action.model_dump(exclude_none=True)
		return None

	def errors(self) -> list[str]:
		"""Get all errors from history"""
		return [h.result.error for h in self.history if h.result.error]

	def final_result(self) -> None | str:
		"""Final result from history"""
		if self.history and self.history[-1].result.extracted_content:
			return self.history[-1].result.extracted_content
		return None

	def is_done(self) -> bool:
		"""Check if the agent is done"""
		if self.history and self.history[-1].result.is_done:
			return self.history[-1].result.is_done
		return False

	def has_errors(self) -> bool:
		"""Check if the agent has any errors"""
		return len(self.errors()) > 0

	def urls(self) -> list[str]:
		"""Get all unique URLs from history"""
		return [h.state.url for h in self.history if h.state.url]

	def screenshots(self) -> list[str]:
		"""Get all screenshots from history"""
		return [h.state.screenshot for h in self.history if h.state.screenshot]

	def action_names(self) -> list[str]:
		"""Get all action names from history"""
		return [list(action.keys())[0] for action in self.model_actions()]

	def model_thoughts(self) -> list[AgentBrain]:
		"""Get all thoughts from history"""
		return [h.model_output.current_state for h in self.history if h.model_output]

	def model_outputs(self) -> list[AgentOutput]:
		"""Get all model outputs from history"""
		return [h.model_output for h in self.history if h.model_output]

	# get all actions with params
	def model_actions(self) -> list[dict]:
		"""Get all actions from history"""
		outputs = []
		for h in self.history:
			if h.model_output:
				output = h.model_output.action.model_dump(exclude_none=True)
				# should have only one key and param_model
				key = list(output.keys())[0]
				params = output[key]

				# convert index to xpath if available
				if 'index' in params:
					selector_map = h.state.selector_map
					index = params['index']
					if index in selector_map:
						params['xpath'] = selector_map[index]

				outputs.append(output)
		return outputs

	def action_results(self) -> list[ActionResult]:
		"""Get all results from history"""
		return [h.result for h in self.history if h.result]

	def extracted_content(self) -> list[str]:
		"""Get all extracted content from history"""
		return [h.result.extracted_content for h in self.history if h.result.extracted_content]

	def model_actions_filtered(self, include: list[str] = []) -> list[dict]:
		"""Get all model actions from history as JSON"""
		outputs = self.model_actions()
		result = []
		for o in outputs:
			for i in include:
				if i == list(o.keys())[0]:
					result.append(o)
		return result


class AgentError:
	"""Container for agent error handling"""

	VALIDATION_ERROR = 'Invalid model output format. Please follow the correct schema.'
	RATE_LIMIT_ERROR = 'Rate limit reached. Waiting before retry.'
	NO_VALID_ACTION = 'No valid action found'

	@staticmethod
	def format_error(error: Exception) -> str:
		"""Format error message based on error type"""
		if isinstance(error, ValidationError):
			return f'{AgentError.VALIDATION_ERROR}\nDetails: {str(error)}'
		if isinstance(error, RateLimitError):
			return AgentError.RATE_LIMIT_ERROR
		return f'Unexpected error: {str(error)}\nStacktrace:\n{traceback.format_exc()}'
