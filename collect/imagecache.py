# /collect/imagecache.py
# -*- coding: utf-8 -*-

import os
import urllib.request

class ImageCache:
	def __init__(self, url: str = None, identifier: str = None, cache_dir: str = "cache/images"):
		if not url or not identifier:
			raise ValueError("url and identifier are required.")

		self.url = url
		self.identifier = identifier
		
		# Create cache directory if it doesn't exist
		if not os.path.exists(cache_dir):
			os.makedirs(cache_dir)

		self.cache_dir = cache_dir
	
	def cache_file_name(self) -> str:
		parsed_url: any = urllib.parse.urlparse(self.url)
		path = parsed_url.path


		last_dot = path.rfind('.')
		if last_dot == -1:
			raise ValueError("The URL does not contain a file extension.")
		extension = path[last_dot:]
		#extension: str = mimetypes.guess_extension(self.url)
		filename = "".join([self.identifier, extension])
		return filename

	def cache_file_path(self) -> str:
		filename: str = self.cache_file_name()
		return os.path.join(self.cache_dir, filename)

	def read_image_from_url(self) -> bool:
		"""Downloads the image from the URL and saves the image to the cache file path.."""
		try:
			with urllib.request.urlopen(self.url) as response:
				with open(self.cache_file_path(), 'wb') as out_file:
					out_file.write(response.read())
			return True
		except Exception as e:
			print(f"Error: {e}")
			return False

	def load_cache(self) -> bool:
		"""Loads the image from the cache file path if it exists, otherwise it downloads the image from the URL."""
		cache_file_path: str = self.cache_file_path()
		if os.path.exists(cache_file_path):
			return True
		else:
			return self.read_image_from_url()

	def get_image_path(self) -> str:
		"""Ensures the image is cached and returns the local path to the image."""
		if self.load_cache():
			return self.cache_file_path()
		else:
			raise FileNotFoundError("The image could not be loaded or downloaded.")
	
if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
