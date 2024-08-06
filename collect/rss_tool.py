# /collect/rss_tool.py
# -*- coding: utf-8 -*-

import json
import os
import requests
import xml.etree.ElementTree as ElementTree
from xml.etree.ElementTree import Element
from datetime import datetime, timedelta
from typing import Generator
from requests.models import PreparedRequest, Request, Response

class RssTool:
	def __init__(self, url: str, cache_duration: int = 28800, cache_file: str = "rss_cache.json"):
		self.url: str = url
		self.cache_file: str = cache_file
		self.cache_duration: timedelta = timedelta(seconds=cache_duration)
		self._last_fetch_time: datetime | None = None
		self._cache: list[dict[str, str]] = []
		self._load_cache_from_file()
	
	def fetch(self) -> Generator[dict[str, str], None, None]:
		if self._is_cache_valid():
			for item in self._cache:
				yield item
		else:
			self._cache = self._update_cache()
			self._save_cache_to_file()
			for item in self._cache:
				yield item

	def _is_cache_valid(self) -> bool:
		"""Check if the cached data is still valid."""
		if self._last_fetch_time is None:
			return False
		return datetime.now() - self._last_fetch_time < self.cache_duration

	def _update_cache(self) -> list[dict[str, str]]:
		"""Fetch data from the URL and update the cache."""
		response: Response = requests.get(self.url)
		root: Element = ElementTree.fromstring(response.content)

		new_cache: list = []
		for item in root.findall(".//item"):
			title: str = item.find("title").text
			link: str = item.find("link").text
			new_cache.append({"title": title, "link": link})

		self._last_fetch_time = datetime.now()
		return new_cache

	def _load_cache_from_file(self):
		"""Load cache and last fetch time from a file."""
		if os.path.exists(self.cache_file):
			with open(self.cache_file, "r") as file:
				data = json.load(file)
				self._cache = data.get("cache", [])
				last_fetch_time_str = data.get("last_fetch_time")
				if last_fetch_time_str:
					self._last_fetch_time = datetime.fromisoformat(last_fetch_time_str)

	def _save_cache_to_file(self):
		"""Save cache and last fetch time to a file."""
		data = {
			"cache": self._cache,
			"last_fetch_time": self._last_fetch_time.isoformat() if self._last_fetch_time else None
		}
		with open(self.cache_file, "w") as file:
			json.dump(data, file, indent="\t")

if __name__ == "__main__":
	import sys
	def _test() -> None:
		url = "https://www.beckett.com/news/feed/"
		cache_file = "cache/becket_rss.json"
		rss_tool = RssTool(url, cache_duration=28800, cache_file=cache_file)
		for item in rss_tool.fetch():
			print(item)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")

