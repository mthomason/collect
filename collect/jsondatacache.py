# /collect/promptchat.py
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Final, List, Dict

class JSONDataCache:
	_DATA_KEY_ID: Final[str] = "identifier"
	_DATA_KEY_TITLE: Final[str] = "headline"
	_DATA_KEY_TIMESTAMP: Final[str] = "timestamp"

	def __init__(self, file_path: str, max_record_age: int = 30):
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
		self._data = [record for record in self._data if datetime.fromisoformat(record[JSONDataCache._DATA_KEY_TIMESTAMP]) > threshold_date]
		self._save_json_data()

	def save(self) -> None:
		"""Save the data to the JSON file."""
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

if __name__ == '__main__':
	import sys

	def _test() -> None:
		cache = JSONDataCache('cache/test_cache.json', max_record_age=1)
		cache.add_record("Record 1", "1")
		cache.add_record("Record 2", "2")
		cache.add_record("Record 3", "3")
		cache.add_record("Record 4", "4")
		cache.add_record("Record 5", "5")
		cache.save()

		# Check that all records exist
		assert cache.record_exists("1")
		assert cache.record_exists("2")
		assert cache.record_exists("3")
		assert cache.record_exists("4")
		assert cache.record_exists("5")

		# Check that a non-existent record does not exist
		assert not cache.record_exists("6")

		# Check that we can find a record by ID
		record = cache.find_record_by_id("3")
		assert record is not None
		assert record[JSONDataCache._DATA_KEY_TITLE] == "Record 3"

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
