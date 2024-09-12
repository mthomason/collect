#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import platform
import requests
import logging

from requests.models import Request, Response
from typing import Final

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

	def fetch(self) -> Response:
		"""Fetch data from the given URL."""
		return self.get()

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
