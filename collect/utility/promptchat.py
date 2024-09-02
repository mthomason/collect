#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openai
import requests
import os
import json
import logging
import uuid

from typing import Iterator, Dict, List, Any
from io import StringIO
from abc import ABC, abstractmethod
from .core.jsondatacache import JSONDataCache

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

class PromptPersonalityFunctional(PromptPersonality):
	_cache_pruned: bool = False
	def __init__(self, name: str, context: str, prompts: list[str], functions: list[dict[str, any]]):
		super().__init__(name, context, prompts, functions)
		self._cache: JSONDataCache = JSONDataCache(f"cache/{self._uuid.lower()}_prompt_cache.json")
		if not self._cache_pruned:
			self._cache.prune_and_save()
			self._cache_pruned = True

		self.results: list[dict[str, str]] = []


class PromptPersonalityAuctioneer(PromptPersonality):
	_cache_pruned: bool = False
	def __init__(self):
		self._cache: JSONDataCache = JSONDataCache("cache/auctioneer_headlines.json")
		self._open_ai_model: str = "gpt-4o-mini"
		if not self._cache_pruned:
			self._cache.prune_and_save()
			self._cache_pruned = True

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

	def _generate_prompt(self, headlines: List[Dict[str, str]], template: str) -> str:
		buffer_prompt = StringIO()
		buffer_prompt.write(template)
		buffer_prompt.write("\n```json\n")
		buffer_prompt.write(json.dumps(headlines, indent="\t"))
		buffer_prompt.write("\n```\n\n")
		return buffer_prompt.getvalue()
	
	def _handle_api_response(self, response: requests.Response) -> Dict[str, Any]:
		if response.status_code != 200:
			logger.error(f"API request failed. Status Code: {response.status_code}. Response: {response.text}.")
			response.raise_for_status()
		return response.json()

	def _cache_headlines(self, headlines: list[dict[str, str]]) -> None:
		for headline in headlines:
			self._cache.add_record_if_not_exists(
				title=headline['headline'],
				record_id=headline['identifier']
			)
		self._cache.save()

	def _fetch_headlines_from_cache(self, headline_ids: list[str]) -> list[dict[str, str]]:
		return [
			self._cache.find_record_by_id(headline_id)
			for headline_id in headline_ids
			if self._cache.record_exists(headline_id)
		]

	def _request_openai_headlines(self, json_data: dict[str, any]) -> dict[str, any]:
		url = "https://api.openai.com/v1/chat/completions"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.apikey}",
		}
		response = requests.post(url=url, headers=headers, json=json_data)
		return self._handle_api_response(response)


	def get_headlines(self) -> iter:
		
		requested_headline_ids: list[str] = [headline["identifier"] for headline in self.headlines]
		cached_headline_ids: list[str] = [id_ for id_ in requested_headline_ids if self._cache.record_exists(id_)]
		uncached_headline_ids: list[str] = [id_ for id_ in requested_headline_ids if id_ not in cached_headline_ids]

		assert len(requested_headline_ids) == len(uncached_headline_ids) + len(self._fetch_headlines_from_cache(requested_headline_ids)), \
			"Mismatch in headline counts."


		if uncached_headline_ids:
			uncached_headlines: list[dict[str,str]] = [
				self.headlines[requested_headline_ids.index(id_)]
				for id_ in uncached_headline_ids
			]

			assert len(uncached_headlines) == len(uncached_headline_ids), "Mismatch in uncached headlines."

			prompt_content: str = self._generate_prompt(uncached_headlines, self.prompts[0])
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
				headlines: list[dict[str, str]] = json.loads(response_data['choices'][0]['message']['function_call']['arguments'])['headlines']
				self._cache_headlines(headlines)
				headlines.extend(self._fetch_headlines_from_cache(cached_headline_ids))
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

		else:  # If all headlines are cached, return them
			return iter(self._fetch_headlines_from_cache(requested_headline_ids))

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
