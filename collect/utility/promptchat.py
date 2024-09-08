#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
import json
import logging
import uuid

from io import StringIO
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PromptPersonality(ABC):
	def __init__(self, name: str, context: str, prompts: list[str], functions: list[dict[str, any]] = []):
		self.name: str = name
		self.context: str = context
		self.prompts: list[str] = prompts
		self.functions: list[dict[str, any]] = functions
		self._uuid = uuid.uuid5(uuid.NAMESPACE_DNS, name)

	@abstractmethod
	def generate_response(self, prompt: str) -> str:
		pass

class PromptPersonalityAuctioneer(PromptPersonality):
	def __init__(self):
		self._open_ai_model: str = "gpt-4o-mini"
		self.headlines: list[dict[str, str]] = []
		super().__init__("Auctioneer", "", [])
		self.functions = None
		try:
			with open('prompts/context_headlines.json') as f:
				data: dict = json.load(f)
				self.context = data["context"]
				self.prompt_start = data["prompt"]
		except FileNotFoundError as fe:
			s: str = "The file 'prompts/context_headlines.json' was not found."
			logger.error(s)
			raise ValueError(s) from fe

		try:
			with open('prompts/function_headlines_function.json') as f:
				data: dict = json.load(f)
				self.functions = [data]
		except FileNotFoundError as fe:
			s: str = "The file 'prompts/function_headlines_function.json' was not found."
			logger.error(s)
			raise ValueError(s) from fe

		self.prompts = [self.prompt_start]
	
	@property
	def apikey(self) -> str:
		api_key = os.getenv("OPENAI_API_KEY")
		if not api_key:
			s: str = "OpenAI API key is missing. Ensure it is set in the environment variables."
			logger.error(s)
			raise ValueError(s)
		return api_key

	def __del__(self):
		self.headlines.clear()

	def add_headline(self, id: str, headline: str, ) -> None:
		self.headlines.append({
			"identifier": id,
			"headline": headline
		})

	def generate_response(self, prompt: str) -> str:
		return f"{self.name}: {prompt}"

	def _generate_prompt(self, template: str) -> str:
		buffer_prompt = StringIO()
		buffer_prompt.write(template)
		buffer_prompt.write("\n```json\n")
		buffer_prompt.write(json.dumps(self.headlines, indent="\t"))
		buffer_prompt.write("\n```\n\n")
		return buffer_prompt.getvalue()
	
	def _handle_api_response(self, response: requests.Response) -> dict[str, any]:
		if response.status_code != 200:
			logger.error(f"API request failed. Status Code: {response.status_code}. Response: {response.text}.")
			response.raise_for_status()
		return response.json()

	def _request_openai_headlines(self, json_data: dict[str, any]) -> dict[str, any]:
		url = "https://api.openai.com/v1/chat/completions"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.apikey}",
		}
		response = requests.post(url=url, headers=headers, json=json_data)
		return self._handle_api_response(response)

	def get_headlines(self) -> iter:
		prompt_content: str = self._generate_prompt(self.prompts[0])
		logger.info(f"Prompt: {prompt_content}")

		json_data: dict[str, any] = {
			"model": self._open_ai_model,
			"messages": [
				{"role": "system", "content": self.context},
				{"role": "user", "content": prompt_content},
			],
			"functions": self.functions,
			"function_call": {"name": "headlines_function"},
		}

		try:
			response_data: dict[str, any] = self._request_openai_headlines(json_data)
			headlines: list[dict[str, str]] = json.loads(
				response_data['choices'][0]['message']['function_call']['arguments']
			)['headlines']
			return iter(headlines)

		except requests.RequestException as e:
			s: str = f"API request failed: {type(e).__name__} - {e}"
			logger.error(s)
			raise ChildProcessError(s) from e

		except (json.JSONDecodeError, KeyError) as e:
			s: str = f"Error parsing API response: {type(e).__name__} - {e}"
			logger.error(s)
			raise ChildProcessError(s) from e

		except Exception as e:
			s: str = f"Unexpected error: {type(e).__name__} - {e}"
			logger.error(s)
			raise RuntimeError(s) from e

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
