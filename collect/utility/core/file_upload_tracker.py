#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class FileUploadTracker:
	def __init__(self, cache_dir: str):
		self.cache_dir: Path = Path(cache_dir)
		self.cache_file: Path = self.cache_dir / "upload_cache.json"
		self.uploaded_files = self._load_cache()

	def _load_cache(self) -> Dict[str, str]:
		"""Load the cache of uploaded file hashes from the cache file."""
		if not self.cache_file.exists():
			return {}
		
		with open(self.cache_file, 'r') as f:
			try:
				return json.load(f)
			except json.JSONDecodeError:
				logging.error(f"Error loading cache file: {self.cache_file}")
				logging.error("Creating a new empty cache file.")
				return {}

	def _save_cache(self):
		"""Save the current cache of uploaded file hashes to the cache file."""
		with open(self.cache_file, 'w') as f:
			json.dump(self.uploaded_files, f, indent="\t")

	def _hash_file(self, file_path: str) -> str:
		"""Generate a hash for the given file using SHA-256."""
		hasher = hashlib.sha256()
		with open(file_path, 'rb') as f:
			for chunk in iter(lambda: f.read(4096), b''):
				hasher.update(chunk)
		return hasher.hexdigest()

	def has_changed(self, file_path: str) -> bool:
		"""Check if the file has changed since it was last uploaded."""
		if not os.path.exists(file_path):
			raise FileNotFoundError(f"File not found: {file_path}")
			
		file_hash = self._hash_file(file_path)
		file_name = Path(file_path).name
		previous_hash = self.uploaded_files.get(file_name)
		
		# Return True if the file is not in the cache or the hash has changed
		return previous_hash != file_hash

	def is_uploaded(self, file_path: str) -> bool:
		"""Check if the file has already been uploaded based on its name and hash."""
		if not os.path.exists(file_path):
			raise FileNotFoundError(f"File not found: {file_path}")
		file_name = Path(file_path).name
		file_hash = self._hash_file(file_path)
		return self.uploaded_files.get(file_name) == file_hash

	def mark_as_uploaded(self, file_path: str):
		"""Mark the file as uploaded by saving its name and hash in the cache."""
		file_name = Path(file_path).name
		file_hash = self._hash_file(file_path)
		self.uploaded_files[file_name] = file_hash
		self._save_cache()

	def cleanup_cache(self):
		"""Optional: Clean up the cache file if needed to free up space."""
		raise NotImplementedError("Cleanup logic is not implemented.")

if __name__ == "__main__":
	import sys

	def _test():
		cache_dir = "cache"
		tracker = FileUploadTracker(cache_dir)
		
		test_file = "httpd/style.css"
		
		if tracker.has_changed(test_file):
			print("File has already been uploaded.")
			tracker.mark_as_uploaded(test_file)
		else:
			print("File is new, uploading...")

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
