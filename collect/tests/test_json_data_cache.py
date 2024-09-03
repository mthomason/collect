import unittest
from unittest.mock import patch, mock_open
from datetime import datetime, timezone, timedelta
import json
import os
from collect.utility.core.jsondatacache import JSONDataCache

class TestJSONDataCache(unittest.TestCase):
	
	def setUp(self):
		self.test_file_path = "test_cache.json"
		self.mock_data = [
			{
				JSONDataCache._DATA_KEY_ID: "1",
				JSONDataCache._DATA_KEY_TITLE: "Title 1",
				JSONDataCache._DATA_KEY_TIMESTAMP: (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
			},
			{
				JSONDataCache._DATA_KEY_ID: "2",
				JSONDataCache._DATA_KEY_TITLE: "Title 2",
				JSONDataCache._DATA_KEY_TIMESTAMP: (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
			}
		]
	
	@patch("builtins.open", new_callable=mock_open, read_data="[]")
	@patch("os.path.exists", return_value=False)
	def test_load_json_data_file_not_exist(self, mock_exists, mock_open_file):
		cache = JSONDataCache(self.test_file_path)
		self.assertEqual(cache._data, [])
	
	@patch("builtins.open", new_callable=mock_open)
	@patch("os.path.exists", return_value=True)
	def test_load_json_data(self, mock_exists, mock_open_file):
		mock_open_file.return_value.read.return_value = json.dumps(self.mock_data)
		cache = JSONDataCache(self.test_file_path)
		self.assertEqual(len(cache._data), 2)

	@patch("builtins.open", new_callable=mock_open)
	def test_save_json_data(self, mock_open_file):
		cache = JSONDataCache(self.test_file_path)
		cache._data = self.mock_data
		cache.save()
		mock_open_file().write.assert_called_once()

	@patch("builtins.open", new_callable=mock_open)
	def test_prune_old_records(self, mock_open_file):
		cache = JSONDataCache(self.test_file_path, max_record_age=7)
		cache._data = self.mock_data
		cache.prune_and_save()
		self.assertEqual(len(cache._data), 1)
	
	def test_add_record(self):
		cache = JSONDataCache(self.test_file_path)
		cache._data = []
		cache.add_record("New Title", "3")
		self.assertEqual(len(cache._data), 1)
		self.assertTrue(cache.record_exists("3"))
	
	def test_find_title_by_id(self):
		cache = JSONDataCache(self.test_file_path)
		cache._data = self.mock_data
		title = cache.find_title_by_id("1")
		self.assertEqual(title, "Title 1")
	
	def test_find_record_by_id(self):
		cache = JSONDataCache(self.test_file_path)
		cache._data = self.mock_data
		record = cache.find_record_by_id("2")
		self.assertIsNotNone(record)
		self.assertEqual(record[JSONDataCache._DATA_KEY_TITLE], "Title 2")
	
	def test_record_exists(self):
		cache = JSONDataCache(self.test_file_path)
		cache._data = self.mock_data
		exists = cache.record_exists("2")
		self.assertTrue(exists)
	
	def test_add_record_if_not_exists(self):
		cache = JSONDataCache(self.test_file_path)
		cache._data = []
		cache.add_record_if_not_exists("Title 3", "3")
		self.assertTrue(cache.record_exists("3"))
	
	def tearDown(self):
		if os.path.exists(self.test_file_path):
			os.remove(self.test_file_path)

if __name__ == "__main__":
	unittest.main()
