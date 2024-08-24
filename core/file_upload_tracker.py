#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import json
from pathlib import Path
from typing import Dict

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
		if self.is_uploaded(file_path):
			return True
		file_hash = self._hash_file(file_path)
		file_name = Path(file_path).name
		changed: bool = self.uploaded_files.get(file_name) != file_hash
		return changed

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
		
		if tracker.is_uploaded(test_file):
			print("File has already been uploaded.")
		else:
			print("File is new, uploading...")
			tracker.mark_as_uploaded(test_file)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
