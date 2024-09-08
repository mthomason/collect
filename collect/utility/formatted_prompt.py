#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import requests
import uuid

from typing import Iterator
from io import StringIO

logger = logging.getLogger(__name__)

class PromptPersonalityFunctional:

	def __init__(
			self,
			apikey: str,
			name: str,
			context: str,
			prompt: str,
			function: dict[str, any]
		):
		if not apikey:
			raise ValueError("OpenAI API key is missing. Ensure it is set in the environment variables.")
		self._apikey: str = apikey
		self._name: str = name
		self._context: str = context
		self._prompt: str = prompt
		self._function: dict[str, any] = function
		self._uuid = uuid.uuid5(uuid.NAMESPACE_DNS, name)

		self.results: list[dict[str, str]] = []
	
	@property
	def prompt(self) -> str:
		return self._prompt[0]

	@property
	def prompt_items(self) -> list[dict[str, str]]:
		return self._prompt_items
	
	@property.setter
	def prompt_items(self, items: list[dict[str, str]]) -> None:
		self._prompt_items = items

	def add_prompt_item(self, id: str, item: str) -> None:
		self._prompt_items.append({"identifier": id, "item": item})

	def _generate_prompt(self) -> str:
		prompt_data = json.dumps(self._prompt_items, indent="\t")
		buffer_prompt = StringIO()
		buffer_prompt.write(self._prompt)
		buffer_prompt.write("\n```json\n")
		buffer_prompt.write(prompt_data)
		buffer_prompt.write("\n```\n\n")
		return buffer_prompt.getvalue()

	def _handle_api_response(self, response: requests.Response) -> dict[str, any]:
		if response.status_code != 200:
			logger.error(f"API request failed. Status Code: {response.status_code}. Response: {response.text}.")
			response.raise_for_status()
		return response.json()

	def _request_chat_completion_functional(self) -> dict[str, any]:
		prompt_content: str = self._generate_prompt()
		url = "https://api.openai.com/v1/chat/completions"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self._apikey}",
		}
		functions: list[dict[str, any]] = [self._function]
		json_data: dict[str, any] = {
			"model": self._open_ai_model,
			"messages": [
				{"role": "system", "content": self._context},
				{"role": "user", "content": prompt_content},
			],
			"functions": functions,
			"function_call": {"name": self._functions["name"]},
		}
		response = requests.post(url=url, headers=headers, json=json_data)
		functions.clear()
		return self._handle_api_response(response)

	def get_results(self) -> Iterator[dict[str, str]]:

		if len(self._prompt_items) == 0:
			raise ValueError("No prompt items found. Please add prompt items before calling this method.")



		return iter(self.results)

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
