#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import json
import time
from unittest.mock import patch, mock_open
from urllib.robotparser import RobotFileParser
from requests import Response
from collect.utility.core.caching_robot_file_parser import CachingRobotFileParser

class TestCachingRobotFileParser(unittest.TestCase):

	@patch("collect.utility.core.caching_robot_file_parser.CachingRobotFileParser.get")
	@patch("os.path.exists")
	@patch("builtins.open", new_callable=mock_open)
	def test_load_robots_txt_from_cache(self, mock_open, mock_exists, mock_get):
		mock_exists.return_value = True
		mock_open().read.return_value = json.dumps({
			"timestamp": time.time(),
			"robots_txt": "User-agent: *\nDisallow: /private"
		})
		
		parser = CachingRobotFileParser(domain="example.com")
		parser.load_robots_txt()

		self.assertTrue(parser._loaded)
		#self.assertEqual(parser._robots_txt, "User-agent: *\nDisallow: /private")
		mock_get.assert_not_called()

	@patch("collect.utility.core.caching_robot_file_parser.CachingRobotFileParser.get")
	@patch("os.path.exists")
	@patch("builtins.open", new_callable=mock_open)
	def test_load_robots_txt_from_web(self, mock_open, mock_exists, mock_get):
		mock_exists.return_value = False
		mock_response = Response()
		mock_response.status_code = 200
		mock_response._content = b"User-agent: *\nDisallow: /private"
		mock_get.return_value = mock_response

		parser = CachingRobotFileParser(domain="example.com")
		parser.load_robots_txt()

		self.assertTrue(parser._loaded)
		#self.assertEqual(parser._robots_txt, "User-agent: *\nDisallow: /private")
		mock_open().write.assert_called()
	
	@patch("collect.utility.core.caching_robot_file_parser.CachingRobotFileParser.get")
	@patch("os.path.exists")
	@patch("builtins.open", new_callable=mock_open)
	def test_load_robots_txt_failed_fetch(self, mock_open, mock_exists, mock_get):
		mock_exists.return_value = False
		mock_response = Response()
		mock_response.status_code = 404
		mock_get.return_value = mock_response

		parser = CachingRobotFileParser(domain="example.com")
		parser.load_robots_txt()

		self.assertTrue(parser._loaded)
		#self.assertEqual(parser._robots_txt, "")
	
	def test_can_fetch(self):
		parser = CachingRobotFileParser(domain="example.com")
		parser.load_robots_txt_from_text("User-agent: *\nDisallow: /private")

		result = parser.can_fetch("TestBot/1.0", "https://example.com/private")
		self.assertFalse(result)

		result = parser.can_fetch("TestBot/1.0", "https://example.com/public")
		self.assertTrue(result)

if __name__ == "__main__":
	unittest.main()

