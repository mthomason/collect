# /collect/promptchat.py
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Final, List, Dict

class JSONDataCache:
	_DATA_KEY_ID: Final[str] = "id"
	_DATA_KEY_TITLE: Final[str] = "title"
	_DATA_KEY_TIMESTAMP: Final[str] = "timestamp"

	def __init__(self, file_path: str, max_record_age: int = 14):
		self.file_path: str = file_path
		self.max_record_age = max_record_age
		self._data = self._load_json_data()

	def _load_json_data(self) -> List[Dict]:
		"""Load data from the JSON file, returning an empty list if the file doesn't exist."""
		if not os.path.exists(self.file_path):
			return []
		with open(self.file_path, 'r') as file:
			return json.load(file)

	def _save_json_data(self) -> None:
		"""Save the current data to the JSON file."""
		with open(self.file_path, 'w') as file:
			json.dump(self._data, file, indent="\t", skipkeys=True)

	def _prune_old_records(self) -> None:
		"""Remove records older than the specified max record age."""
		threshold_date = datetime.now(timezone.utc) - timedelta(days=self.max_record_age)
		threshold_date = datetime.now(timezone.utc) #- timedelta(days=self.max_record_age)
		self._data = [record for record in self._data if datetime.fromisoformat(record[JSONDataCache._DATA_KEY_TIMESTAMP]) > threshold_date]
		self._save_json_data()

	def add_record_if_not_exists(self, title: str, record_id: str) -> None:
		"""Add a new record with the given title and ID if it doesn't already exist."""
		if not self.record_exists(record_id):
			self.add_record(title, record_id)

	def add_record(self, title: str, record_id: str) -> None:
		"""Add a new record with the given title and ID."""
		if self.record_exists(record_id):
			raise ValueError(f"Record with ID {record_id} already exists.")
		timestamp = datetime.now(timezone.utc).isoformat()
		new_record = {JSONDataCache._DATA_KEY_TITLE: title, JSONDataCache._DATA_KEY_ID: record_id, JSONDataCache._DATA_KEY_TIMESTAMP: timestamp}
		self._data.append(new_record)
		self._save_json_data()

	def find_title_by_id(self, record_id: str) -> Optional[str]:
		"""Find a title by ID, returning the title if found or None if not."""
		for record in self._data:
			if record[JSONDataCache._DATA_KEY_ID] == record_id:
				return record[JSONDataCache._DATA_KEY_TITLE]
		return None

	def find_record_by_id(self, record_id: str) -> Optional[Dict]:
		"""Find a record by ID, returning the record if found or None if not."""
		for record in self._data:
			if record[JSONDataCache._DATA_KEY_ID] == record_id:
				return record
		return None

	def record_exists(self, record_id: str) -> bool:
		"""Check if a record exists by ID."""
		return any(record[JSONDataCache._DATA_KEY_ID] == record_id for record in self._data)

	def prune_and_save(self) -> None:
		"""Prune old records and save the data."""
		self._prune_old_records()

# Example usage
if __name__ == '__main__':
	#raise ValueError("This script is not meant to be run directly.")

	cache = JSONDataCache('cache/openai_cache_data.json')

	# Prune old records and save
	cache.prune_and_save()

	# Add a new record
	cache.add_record_if_not_exists("Sample Title", "12345")
	cache.add_record_if_not_exists("Sample Title", "12348")
	cache.add_record_if_not_exists("Sample Title2", "12349")
	cache.add_record_if_not_exists("Sample Title3", "1234asdf8")
	cache.add_record_if_not_exists("Sample Title", "12345")
	cache.add_record_if_not_exists("Sample Title", "12348")
	cache.add_record_if_not_exists("Sample Title2", "12349")
	cache.add_record_if_not_exists("Sample Title3", "1234asdf8")

	# Find a record by ID
	record = cache.find_record_by_id("12345")
	print("Record:")
	print(record)

	# Check if a record exists
	exists = cache.record_exists("12345")
	print("Record exists:")
	print(exists)

	title1 = cache.find_title_by_id("12345")
	print(title1)
	title2 = cache.find_title_by_id("12346")
	print(title2)
	title3 = cache.find_title_by_id("12349")
	print(title3)

	cache.prune_and_save()

