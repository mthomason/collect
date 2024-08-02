# /collect/promptchat.py
# -*- coding: utf-8 -*-

import json
from typing import List, Dict, Any
from abc import ABC, abstractmethod

# Below is an abstract base class for prompt personalities.  Each
# personality is a subclass of this class.  Each personality has a
# name, a context, and a list of prompts.  The context is a string
# that describes the personality.  The prompts are a list of strings
# that are used to generate the personality's responses.
class PromptPersonality(ABC):
	def __init__(self, name: str, context: str, prompts: List[str]):
		self.name = name
		self.context = context
		self.prompts = prompts
		return

	@abstractmethod
	def generate_response(self, prompt: str) -> str:
		return

class PromptPersonalityAuctioneer (PromptPersonality):
	def __init__(self):
		self.name = "Auctioneer"
		self.functions: list[dict[str, any]] = []

		# Read the context from the dictionary in the file named `context_headlines.json`.  You need " \
		# to read the the field named `context` from the file with the key named `context`.
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
				self.functions.append(data)
				print(self.functions[0])
		except FileNotFoundError:
			raise ValueError("The file 'prompts/function_headlines_function.json' was not found.")

		return

	def generate_response(self, prompt: str) -> str:
		return f"{self.name}: {prompt}"


if __name__ == "__main__":
	# Test the classes and methods in this file.
	auctioneer = PromptPersonalityAuctioneer()
	print(auctioneer.context)
	print(auctioneer.generate_response("Hello, world!"))

	#raise ValueError("This script is not meant to be run directly.")
