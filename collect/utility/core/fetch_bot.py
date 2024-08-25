#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import platform
from random import randint
import requests
import time

from requests.models import Request, Response
from typing import Final
from urllib.parse import urlparse, ParseResult
from urllib.robotparser import RobotFileParser

class FetchBot:

	def __init__(
			self,
			url: str,
			cache_directory: str | None = None,
			user_agent: str | None = "HobbyBot/1.0"
		):
		self._user_agent = user_agent
		self._url: str = url
		self._cache_directory: str = cache_directory or "cache"
		self._request: Request = Request()
		self._response: Response | None = None
		
		# See warning at https://docs.python.org/3/library/urllib.request.html
		if str.lower(platform.system()) == "darwin":
			os.environ["no_proxy"] = "*"
	
	@property
	def request_headers(self) -> dict[str, str]:
		"""Return the headers for the request."""
		return {
				"User-Agent": self._user_agent
			}

	def get(self, url: str | None = None) -> Response:
		"""Send a GET request to the given URL."""
		self._request.method = "GET"
		_request_url: str = url or self._url
		self._request.url = _request_url
		self._request.headers = self.request_headers
		self._response = requests.get(self._request.url, headers=self._request.headers)
		return self._response
	
	def cache_robots_txt(self, data: str, robots_url: str, cache_file_path: str) -> bool:
		"""Cache the robots.txt file for the given URL."""
		cache_data: dict[str, any] = {
			"url": robots_url,
			"timestamp": time.time(),
			"robots_txt": data
		}

		cache_file_path: str = self.cache_file_path()
		with open(cache_file_path, "w", encoding="utf-8") as cache_file:
			json.dump(cache_data, cache_file, ensure_ascii=False, indent="\t")

		return cache_data

	def fetch(self) -> Response:
		"""Fetch data from the given URL."""
		return self.get()
	
	@property
	def robots_url(self) -> str:
		"""Return the URL for the robots.txt file."""
		parsed_url: ParseResult = urlparse(self._url)
		return f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

	def cache_robots_txt_ttl(self) -> int:
		"""Return the time-to-live for the robots.txt cache."""
		return 24 * 60 * 60 * randint(5, 9) # 5-9 days

	def cache_file_path(self) -> str:
		"""Return the path to the cache file."""
		parsed_url: ParseResult = urlparse(self._url)
		domain_name: str = parsed_url.netloc.replace(".", "_")
		return os.path.join(self._cache_directory, f"robots_txt_{domain_name}.json")

	def obey_robots_txt(self) -> bool:
		"""
		Check the robots.txt file for the given URL.  Return True if allowed,
		False if disallowed.
		"""

		cache_file_path: str = self.cache_file_path()
		cache_exist: bool = os.path.exists(cache_file_path)
		cache_is_valid: bool = False
		allowed_query: bool = False
		cache_data: dict = {}

		if cache_exist:
			with open(cache_file_path, "r") as cache_file:
				cache_data: dict = json.load(cache_file)
				cache_timestamp: float = cache_data["timestamp"]
				cache_is_valid = time.time() - cache_timestamp < self.cache_robots_txt_ttl()
		
		if cache_is_valid:
			robots_txt: str = cache_data["robots_txt"]
			robot_parser: RobotFileParser = RobotFileParser()
			robot_parser.parse(robots_txt.splitlines())
			if robot_parser.can_fetch(self._user_agent, self._url):
				allowed_query = True
			else:
				allowed_query = False
		else:
			# Cache is old or doesn't exist.  Fetch the robots.txt file.
			response: Response = self.get(self.robots_url)
			if response.status_code == 200:
				robots_txt = response.text
				robot_parser: RobotFileParser = RobotFileParser()
				robot_parser.parse(robots_txt.splitlines())
				if robot_parser.can_fetch(self._user_agent,
							  			  self._url):
					allowed_query = True
				else:
					allowed_query = False
				self.cache_robots_txt(robots_txt, robots_url=self.robots_url,
						  cache_file_path=cache_file_path)
			else:
				# No robots.txt file found.  Assume it's allowed.
				allowed_query = True

		return allowed_query

if __name__ == "__main__":
	import sys

	def _test():
		fetchbot_: FetchBot = FetchBot("https://www.beckett.com/news/feed/")
		if fetchbot_.obey_robots_txt():
			print("TEST: Allowed by robots.txt.")
		else:
			print("TEST: Disallowed by robots.txt.")
		
		exit(0)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
