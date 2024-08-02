# /collect/promptchat.py
# -*- coding: utf-8 -*-

import openai
import requests
import os
from io import StringIO
import json
from typing import List, Dict, Any
from abc import ABC, abstractmethod

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
	def __init__(self):
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

	def generate_response(self, prompt: str) -> str:
		return f"{self.name}: {prompt}"

	def get_headlines(self, additional_prompt: str):
		openai.api_key = os.getenv("OPENAI_API_KEY")
		openai_model = "gpt-4-turbo"

		buffer_prompt = StringIO()
		buffer_prompt.write(self.prompts[0])
		buffer_prompt.write(additional_prompt)

		prompt_messages: List[Dict[str, str]] = []
		prompt_messages.append({"role": "system", "content": self.context})
		prompt_messages.append({"role": "user", "content": buffer_prompt.getvalue()})

		json_data: dict[str, any] = {"model": openai_model, "messages": prompt_messages}

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
				print(f"Unable to generate response. Status Code: {response.status_code}. Response: {response.text}.")
				return iter([])

			response_data_string: str = response.json()['choices'][0]['message']['function_call']['arguments']
			response_data: dict[str, any] = json.loads(response_data_string)
			return iter(response_data['headlines'])

		except Exception as e:
			print(f"Unable to generate response. Exception: {e}.")
			return iter([])

# Example usage
if __name__ == "__main__":
	auctioneer = PromptPersonalityAuctioneer()
	additional_prompt = """
```html
<ul>
<li><a class="ending_soon" href="https://www.ebay.com/itm/2006-Topps-Chrome-Gold-Superfractors-309-Justin-Verlander-RC-Rookie-1-1-BGS-9-5-/145896558154">2006 Topps Chrome Gold Superfractors #309 Justin Verlander RC Rookie 1/1 BGS 9.5</a></li>
<li><a class="ending_soon" href="https://www.ebay.com/itm/2007-08-UD-Chronology-Autographs-Gold-Michael-Jordan-AUTO-03-10-BGS-9-MINT-BULLS-/135152362719">2007-08 UD Chronology Autographs Gold Michael Jordan AUTO 03/10 BGS 9 MINT BULLS</a></li>
<li><a href="https://www.ebay.com/itm/2024-Panini-National-NSCC-Silver-Pack-Caitlin-Clark-Black-Rookies-RC-1-1-/126598347732">2024 Panini The National NSCC Silver Pack Caitlin Clark Black Rookies RC # 1/1</a></li>
<li><a href="https://www.ebay.com/itm/2023-Upper-Deck-Allure-B-5-Connor-Bedard-16-Bit-Rookie-SSP-Case-Hit-PSA-10-/204909995606">2023 Upper Deck Allure #B-5 Connor Bedard 16-Bit Rookie SSP Case Hit PSA 10</a></li>
<li><a href="https://www.ebay.com/itm/2023-24-Prizm-Victor-Wembanyama-Gold-Sparkle-Rookie-01-24-Jersey-d-1-1-PSA-10-/375561269928">2023-24 Prizm Victor Wembanyama Gold Sparkle Rookie #01/24 Jersey #d 1/1 PSA 10</a></li>
<li><a href="https://www.ebay.com/itm/1956-Topps-135-Mickey-Mantle-Yankees-HOF-Gray-Back-PSA-8-LOOKS-NICER-/365032399222">1956 Topps #135 Mickey Mantle Yankees HOF Gray Back PSA 8 " LOOKS NICER "</a></li>
<li><a href="https://www.ebay.com/itm/2023-Panini-Select-Football-C-J-Stroud-RC-Zebra-Prizm-Die-Cut-SSP-/135167700301">2023 Panini Select Football C.J. Stroud RC Zebra Prizm Die Cut SSP 🔥🔥</a></li>
<li><a href="https://www.ebay.com/itm/Wayne-Gretzky-HOF-Signed-1979-O-Pee-Chee-OPC-Hockey-18-RC-PSA-6-PSA-DNA-10-AUTO-/365032835147">Wayne Gretzky HOF Signed 1979 O-Pee-Chee OPC Hockey #18 RC PSA 6 PSA/DNA 10 AUTO</a></li>
<li><a href="https://www.ebay.com/itm/2002-03-Ultimate-Michael-Jordan-BuyBack-Auto-SP-Game-Floor-Autograph-8-PSA-10-/395561205574">2002-03 Ultimate Michael Jordan BuyBack Auto SP Game Floor Autograph #/8 PSA 10</a></li>
</ul>
```
					 
"""
	headlines_iterator = auctioneer.get_headlines(additional_prompt)
	for headline in headlines_iterator:
		print(f"{headline['headline']}")

