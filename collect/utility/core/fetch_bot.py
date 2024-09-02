#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import platform
import requests
import time
import logging

from requests.models import Request, Response
from typing import Final
from urllib.parse import urlparse, ParseResult
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

class FetchBot:

	_ROBOTS_TXT_TIMEOUT: Final[int] = 24 * 60 * 60 * 7 # 7 days

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
		
		# Set the no_proxy environment variable for macOS.
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
		_response: Response = requests.get(
			self._request.url, headers=self._request.headers
		)
		return _response
	
	def _cache_robots_txt(self, data: str, robots_url: str, cache_file_path: str) -> bool:
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

	def cache_file_path(self) -> str:
		"""Return the path to the cache file."""
		parsed_url: ParseResult = urlparse(self._url)
		domain_name: str = parsed_url.netloc.replace(".", "_")
		return os.path.join(self._cache_directory, f"robots_txt_{domain_name}.json")

	def is_allowed_by_robots_txt(self) -> bool:
		"""
		Check the robots.txt file for the given URL.  Return True if allowed,
		False if disallowed.
		"""

		cache_file_path: str = self.cache_file_path()
		cache_data: dict = {}

		if os.path.exists(cache_file_path):
			try:
				with open(cache_file_path, "r") as cache_file:
					cache_data: dict = json.load(cache_file)
					cache_timestamp: float = cache_data["timestamp"]
					if time.time() - cache_timestamp < FetchBot._ROBOTS_TXT_TIMEOUT:
						robots_txt: str = cache_data["robots_txt"]
					else:
						cache_data = {}
			except json.JSONDecodeError:
				logger.warning(f"Corrupted cache file: {cache_file_path}")
				os.remove(cache_file_path)
				cache_data = {}

		robots_txt: str = ""
		if cache_data:
			robots_txt = cache_data["robots_txt"]
		else:
			# Cache is old or doesn't exist.  Fetch the robots.txt file.
			response: Response = self.get(self.robots_url)
			if response.status_code == 200:
				robots_txt = response.text
				self._cache_robots_txt(
					robots_txt,
					robots_url=self.robots_url,
					cache_file_path=cache_file_path
				)
			else:
				logger.warning(f"Failed to fetch robots.txt from {self.robots_url}")
				logger.warning(f"Using empty robots.txt.")
				robots_txt = ""

		if not robots_txt:
			return True
		else:
			robot_parser: RobotFileParser = RobotFileParser()
			robot_parser.parse(robots_txt.splitlines())
			return robot_parser.can_fetch(self._user_agent, self._url)

if __name__ == "__main__":
	import sys

	def _test():
		fetchbot_: FetchBot = FetchBot("https://www.beckett.com/news/feed/")
		if fetchbot_.is_allowed_by_robots_txt():
			print("TEST: Allowed by robots.txt.")
		else:
			print("TEST: Disallowed by robots.txt.")
		
		exit(0)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
