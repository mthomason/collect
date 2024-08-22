#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import urllib.request

logger = logging.getLogger(__name__)

class ImageCache:
	"""This class is used to cache images from URLs to local files.
	It is used to ensure that images are available locally for processing.
	It requires a URL and an identifier to be provided.
	If the image is not already cached, it will be downloaded and saved to the cache directory.
	The local path to the image can be accessed using the image_path property.
	The cache directory can be specified, otherwise it defaults to "cache/images".

	Keyword arguments:
	* url -- The URL of the image to cache.
	* identifier -- A unique identifier for the image.
	* cache_dir -- The directory to store cached images.
	"""
	def __init__(self, url: str = None, identifier: str = None,
				 cache_dir: str = "cache/images",
				 user_agent: str | None = None):
		if not url or not identifier:
			raise ValueError("url and identifier are required.")
		
		if not os.path.exists(cache_dir):
			os.makedirs(cache_dir)

		self._user_agent: str | None = user_agent
		self.url = url
		self.identifier = identifier
		self._downloaded_image = False
		self.cache_dir = cache_dir

	@property
	def image_path(self) -> str:
		return self._cache_file_path()

	def download_image_if_needed(self) -> bool:
		"""Ensures the image is cached and returns whether the image was downloaded."""
		return self._load_cache()

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

			request: urllib.request.Request
			if not self._user_agent:
				request = urllib.request.Request(self.url)
			else:
				h: dict[str, str] = {'User-Agent': self._user_agent}
				request = urllib.request.Request(self.url, headers=h)

			with urllib.request.urlopen(request) as response:
				image_data: bytes = response.read()
				with open(self.image_path, 'wb') as out_file:
					out_file.write(image_data)
			return True
		except Exception as e:
			logger.error(f"Error downloading image from URL: {self.url}")
			logger.error(f"Error: {e}")
			return False

	def _load_cache(self) -> bool:
		"""Loads the image from the cache file path if it exists, otherwise it downloads the image from the URL."""
		if os.path.exists(self.image_path):
			return True
		else:
			self._downloaded_image = self._read_image_from_url()
			return self._downloaded_image

	def _get_image_path(self) -> str:
		"""Ensures the image is cached and returns the local path to the image."""
		if self._load_cache():
			return self._cache_file_path()
		else:
			raise FileNotFoundError("The image could not be loaded or downloaded.")
	
if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
