#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import openai
import requests
import os
import json
import logging

from core.jsondatacache import JSONDataCache
from io import StringIO
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class PromptPersonality(ABC):
	def __init__(self, name: str, context: str, prompts: list[str], functions: list[dict[str, any]] = []):
		self.name: str = name
		self.context: str = context
		self.prompts: list[str] = prompts
		self.functions: list[dict[str, any]] = functions

	@abstractmethod
	def generate_response(self, prompt: str) -> str:
		pass

class PromptPersonalityAuctioneer(PromptPersonality):
	_cache_pruned: bool = False
	def __init__(self):
		self._cache: JSONDataCache = JSONDataCache("cache/auctioneer_headlines.json")
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
		except FileNotFoundError:
			raise ValueError("The file 'prompts/context_headlines.json' was not found.")

		try:
			with open('prompts/function_headlines_function.json') as f:
				data: dict = json.load(f)
				self.functions = [data]
		except FileNotFoundError:
			raise ValueError("The file 'prompts/function_headlines_function.json' was not found.")

		self.prompts = [self.prompt_start]

	def add_headline(self, id: str, headline: str, ) -> None:
		self.headlines.append({"identifier": id, "headline": headline})

	def clear_headlines(self) -> None:
		self.headlines.clear()

	def additional_prompt(self) -> str:
		buffer: StringIO = StringIO()
		buffer.write("\n```json\n")
		buffer.write(json.dumps(self.headlines, indent="\t"))
		buffer.write("```\n\n")
		return buffer.getvalue()

	def generate_response(self, prompt: str) -> str:
		return f"{self.name}: {prompt}"

	def get_headlines(self) -> iter:

		requested_headline_ids: list[str] = [headline["identifier"] for headline in self.headlines]
		uncached_headline_ids: list[str] = []
		cached_headline_ids: list[str] = []

		for headline_id in requested_headline_ids:
			if not self._cache.record_exists(headline_id):
				uncached_headline_ids.append(headline_id)
			else:
				cached_headline_ids.append(headline_id)

		assert (len(uncached_headline_ids) + len(cached_headline_ids)) == len(requested_headline_ids), "Mismatch in headline counts."

		if (len(uncached_headline_ids) > 0):	# If there are uncached headlines, generate them

			openai.api_key = os.getenv("OPENAI_API_KEY")
			openai_model: str = "gpt-4o-mini"

			buffer_prompt = StringIO()
			buffer_prompt.write(self.prompts[0])
			uncached_headlines: list[dict[str, str]] = []
			for headline_id in uncached_headline_ids:
				uncached_headlines.append(
					self.headlines[requested_headline_ids.index(headline_id)]
				)

			assert len(uncached_headlines) == len(uncached_headline_ids), "No uncached headlines found."

			buffer_prompt.write("\n```json\n")
			buffer_prompt.write(json.dumps(uncached_headlines, indent="\t"))
			buffer_prompt.write("\n```\n\n")

			logger.info(f"Prompt: {buffer_prompt.getvalue()}")

			prompt_messages: list[dict[str, str]] = []
			prompt_messages.append({"role": "system", "content": self.context})
			prompt_messages.append({"role": "user", "content": buffer_prompt.getvalue()})

			json_data: dict[str, any] = {
				"model": openai_model,
				"messages": prompt_messages,
			}

			if self.functions:
				json_data["functions"] = self.functions
				json_data["function_call"] = {"name": "headlines_function"}

			try:
				url = "https://api.openai.com/v1/chat/completions"
				headers = {
					"Content-Type": "application/json",
					"Authorization": "Bearer " + openai.api_key,
				}
				response = requests.post(url=url, headers=headers, json=json_data)

				if response.status_code != 200:
					logger.error(f"Unable to generate response. Status Code: {response.status_code}. Response: {response.text}.")
					return iter([])

				response_s: str = response.json()['choices'][0]['message']['function_call']['arguments']
				response_data: dict[str, any] = json.loads(response_s)

				# Cache the headlines
				cache_ctr: int = 0
				for headline in response_data['headlines']:
					self._cache.add_record_if_not_exists(
						title=headline['headline'],
						record_id=headline['identifier']
						)
					cache_ctr += 1

				if cache_ctr > 0:
					self._cache.save()

				for headline_id in cached_headline_ids:
					headline: dict = self._cache.find_record_by_id(headline_id)
					if headline:
						response_data['headlines'].append(headline)

				return iter(response_data['headlines'])

			except Exception as e:
				logger.error(f"Unable to generate response. Exception: {e}.")
				return iter([])
			
		else: # If all headlines are cached, return them
			headlines: list[dict[str, str]] = []
			for headline_id in requested_headline_ids:
				headline: dict = self._cache.find_record_by_id(headline_id)
				if headline:
					headlines.append(headline)
			return iter(headlines)

	def __del__(self):
		self.headlines.clear()

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
