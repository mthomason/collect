import os
import json
import time
from typing import Callable

class APICache:
	def __init__(self, cache_dir: str = "cache", cache_file: str = "api_cache.json", cache_ttl: int = 8 * 60 * 60):
		self.cache_dir = cache_dir
		self.cache_file = cache_file
		self.cache_ttl = cache_ttl
		if not os.path.exists(self.cache_dir):
			os.makedirs(self.cache_dir)
	
	def cache_file_path(self) -> str:
		return os.path.join(self.cache_dir, self.cache_file)

	def load_cache(self) -> list[dict[str, any]]:
		"""Load the cache from the file if it exists and is not expired."""
		cache_file_path: str = self.cache_file_path()
		if os.path.exists(cache_file_path):
			with open(cache_file_path, 'r') as f:
				cache_data: list[str, dict] = json.load(f)
				if time.time() - cache_data['timestamp'] < self.cache_ttl:
					return cache_data['data']
		return []

	def save_cache(self, data: list[dict[str, any]]):
		"""Save the data to the cache file with the current timestamp."""
		cache_data: dict[str, any] = {
			'data': data,
			'timestamp': time.time()
		}
		with open(self.cache_file_path(), 'w') as f:
			json.dump(cache_data, f, indent=4)

	def cached_api_call(self, func: Callable[[], list[dict[str, any]]], *args) -> list[dict[str, any]]:
		"""Fetches data from the cache or calls the API function and caches the result."""
		cached_data: list[dict[str, any]] = self.load_cache()
		if cached_data:
			return cached_data

		api_data: list[dict[str, any]] = func(*args)
		self.save_cache(api_data)
		return api_data

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
