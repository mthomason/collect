#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import requests

from .gpt_function_prompt import GptFunctionPrompt, GptFunctionProperty
from io import StringIO
from typing import overload

logger = logging.getLogger(__name__)

class PromptPersonalityFunctional:
	"""
		A class used to get the openai chat completion results for a functional prompt.

		This forces the AI to call a function, and to provide the paramaters for the function call.

		Attributes:
			apikey (str): The OpenAI API key.
			model (str): The model to use for the completion. Default is "gpt-4o-mini".
			prompt (GptFunctionPrompt): The functional prompt.  It will have
				json data appended to the prompt to call the function.

		Methods:
			add_prompt_item(item: dict[str, str]) -> None: Add a single item to the prompt.
			add_prompt_item(item: list[dict[str, str]]) -> None: Add a list of items to the prompt.
			add_prompt_item_data(*items: tuple[str, ...]) -> None: Add a list of items to the prompt.
			get_results() -> Iterator[dict[str, str]]: Get the results from the chat completion.

	"""

	def __init__(
			self,
			apikey: str,
			prompt: GptFunctionPrompt,
			model: str = "gpt-4o-mini"
		):
		if not apikey:
			raise ValueError("OpenAI API key is missing. Ensure it is set in the environment variables.")
		self._apikey: str = apikey
		self._model = model
		self._prompt: GptFunctionPrompt = prompt
		self._prompt_items: list[dict[str, str]] = []
	
	def _validate_prompt_item(self, item: dict[str, str]) -> bool:
		return all(key in item for key in self._fun_object_properties())

	def _fun_object_properties(self) -> list[str]:
		fun_param_name: str = self._prompt.function.parameters.required[0]
		fun_prop: GptFunctionProperty = self._prompt.function.parameters.properties[fun_param_name]
		return fun_prop.items.required

	def _generate_prompt(self) -> str:
		prompt_data = json.dumps(self._prompt_items, indent="\t")
		buffer_prompt = StringIO()
		buffer_prompt.write(self._prompt.prompt)
		buffer_prompt.write("\n```json\n")
		buffer_prompt.write(prompt_data)
		buffer_prompt.write("\n```\n\n")
		s: str = buffer_prompt.getvalue()
		buffer_prompt.close()
		return s

	def _handle_api_response(self, response: requests.Response) -> dict[str, any]:
		if response.status_code != 200:
			logger.error(f"API request failed. Status Code: {response.status_code}.")
			logger.error(f"Response: {response.text}.")
			response.raise_for_status()
		return response.json()

	def _request_chat_completion_functional(self) -> dict[str, any]:
		url = "https://api.openai.com/v1/chat/completions"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._apikey}",
		}
		functions: list[dict[str, any]] = [self._prompt.function.to_dict()]
		json_data: dict[str, any] = {
			"model": self._model,
			"messages": [
				{ "role": "system", "content": self._prompt.context },
				{ "role": "user", "content": self._generate_prompt() },
			],
			"functions": functions,
			"function_call": {
				"name": self._prompt.function.name
			},
		}
		response = requests.post(url=url, headers=headers, json=json_data)
		functions.clear()
		json_data.clear()
		return self._handle_api_response(response)

	@overload
	def add_prompt_item(self, item: dict[str, str]) -> None: ...

	def add_prompt_item(self, item: list[dict[str, str]]) -> None:
		if isinstance(item, dict):
			if not self._validate_prompt_item(item):
				raise ValueError("Item does not match the required function parameters.")
			self._prompt_items.append(item)
		elif isinstance(item, list):
			if not all(self._validate_prompt_item(item) for item in item):
				raise ValueError("Item does not match the required function parameters.")
			self._prompt_items.extend(item)

	def add_prompt_item_data(self, *items: tuple[str, ...]) -> None:
		fun_properties: list[str] = self._fun_object_properties()
		for user_item in items:
			item: dict[str, str] = {}
			for i, fun_param_name in enumerate(fun_properties):
				item[fun_param_name] = user_item[i]

			if not self._validate_prompt_item(item):
				raise ValueError("Item does not match the required function parameters.")
			self._prompt_items.append(item)

	def get_results(self) -> list[dict[str, str]]:
		response: dict[str, any] = self._request_chat_completion_functional()
		arguments = json.loads(
			response["choices"][0]["message"]["function_call"]['arguments']
		)
		fun_arguments: list[dict[str, str]] = arguments[self._prompt.function.parameters.required[0]]
		return fun_arguments

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
