#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import logging

from requests import get
from requests.models import Response
from typing import Final
from urllib.parse import urlparse, ParseResult
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

class CachingRobotFileParser:

	_ROBOTS_TXT_TIMEOUT: Final[int] = 24 * 60 * 60 * 7

	def __init__(
			self,
			domain: str | None = None,
			url: str | None = None,
			cache_directory: str = "cache"
		):
		if not domain and not url:
			raise ValueError("Either domain or url is required.")
		self._domain: str = domain or urlparse(url).netloc
		if not self._domain or '.' not in self._domain:
			raise ValueError("Invalid domain.")
		
		self._loaded: bool = False
		self._cache_directory: str = cache_directory
		self._robot_parser: RobotFileParser = RobotFileParser()
		self._robot_parser.modified()

	def get(self, url: str) -> Response:
		"""Wrapper around requests.get for easier mocking in tests."""
		return get(url)

	@property
	def cache_file_path(self) -> str:
		"""Return the path to the cache file for the robots.txt file."""
		return os.path.join(
			self._cache_directory,
			f"robots_txt_{self._domain}.json"
		)

	def load_robots_txt_from_text(self, robots_txt: str) -> None:
		"""Load the robots.txt file from the given text."""
		self._robot_parser.parse(robots_txt.splitlines())
		self._loaded = True
		return

	def load_robots_txt(self):
		robots_url: str = f"https://{self._domain}/robots.txt"
		cache_filepath: str = self.cache_file_path
		robots_txt: str = ""
		cache_data: dict = {}
		if os.path.exists(cache_filepath):
			try:
				with open(cache_filepath, "r") as cache_file:
					cache_data: dict = json.load(cache_file)
					cache_timestamp: float = cache_data["timestamp"]
					if time.time() - cache_timestamp < CachingRobotFileParser._ROBOTS_TXT_TIMEOUT:
						robots_txt: str = cache_data["robots_txt"]
					else:
						cache_data = {}
			except json.JSONDecodeError:
				logger.warning(f"Corrupted cache file: {cache_filepath}")
				os.remove(cache_filepath)
				cache_data = {}

		if cache_data:
			robots_txt = cache_data["robots_txt"]
		else:
			# Cache is old or doesn't exist.  Fetch the robots.txt file.
			response: Response = self.get(robots_url)
			if response.status_code == 200:
				robots_txt = response.text
				self._cache_robots_txt(
					robots_txt,
					robots_url=robots_url
				)
			else:
				logger.warning(f"Failed to fetch robots.txt from {robots_url}")
				logger.warning(f"Using empty robots.txt.")
				robots_txt = ""

		self._robot_parser.parse(robots_txt.splitlines())
		self._loaded = True
		return

	def can_fetch(self, user_agent: str, url: str) -> bool:
		if not self._loaded:
			self.load_robots_txt()
		return self._robot_parser.can_fetch(user_agent, url)

	def _cache_robots_txt(self, data: str, robots_url: str) -> bool:
		"""Cache the robots.txt file for the given URL."""
		cache_data: dict[str, any] = {
			"url": robots_url,
			"timestamp": time.time(),
			"robots_txt": data
		}
		with open(self.cache_file_path, "w", encoding="utf-8") as cache_file:
			json.dump(cache_data, cache_file, ensure_ascii=False, indent="\t")

		return cache_data
