#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import urllib.request

logger = logging.getLogger(__name__)

class ImageCache:
	def __init__(self, url: str = None, identifier: str = None, cache_dir: str = "cache/images"):
		if not url or not identifier:
			raise ValueError("url and identifier are required.")

		self.url = url
		self.identifier = identifier
		self._downloaded_image = False
		
		# Create cache directory if it doesn't exist
		if not os.path.exists(cache_dir):
			os.makedirs(cache_dir)

		self.cache_dir = cache_dir
	
	def _cache_file_name(self) -> str:
		parsed_url: any = urllib.parse.urlparse(self.url)
		last_dot = parsed_url.path.rfind('.')
		if last_dot == -1:
			raise ValueError("The URL does not contain a file extension.")
		filename: str = "".join([self.identifier, parsed_url.path[last_dot:]])
		return filename

	def _cache_file_path(self) -> str:
		filename: str = self._cache_file_name()
		return os.path.join(self.cache_dir, filename)

	def _read_image_from_url(self) -> bool:
		"""Downloads the image from the URL and saves the image to the cache file path.."""
		try:
			with urllib.request.urlopen(self.url) as response:
				with open(self._cache_file_path(), 'wb') as out_file:
					out_file.write(response.read())
			return True
		except Exception as e:
			print(f"Error: {e}")
			return False

	def _load_cache(self) -> bool:
		"""Loads the image from the cache file path if it exists, otherwise it downloads the image from the URL."""
		cache_file_path: str = self._cache_file_path()
		if os.path.exists(cache_file_path):
			return True
		else:
			self._downloaded_image = self._read_image_from_url()
			return self._downloaded_image

	def download_image_if_needed(self) -> bool:
		"""Ensures the image is cached and returns whether the image was downloaded."""
		return self._load_cache()

	@property
	def image_path(self) -> str:
		return self._cache_file_path()

	def _get_image_path(self) -> str:
		"""Ensures the image is cached and returns the local path to the image."""
		if self._load_cache():
			return self._cache_file_path()
		else:
			raise FileNotFoundError("The image could not be loaded or downloaded.")
	
if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
