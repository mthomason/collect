#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import hashlib
import shutil
from datetime import datetime

class FilePathTools(object):

	@staticmethod
	def create_directory_if_not_exists(directory: str) -> None:
		if not os.path.exists(directory):
			os.makedirs(directory)

	@staticmethod
	def backup_file(file_path: str, backup_location: str) -> None:
		if not os.path.isfile(file_path):
			raise FileNotFoundError(f"The file {file_path} does not exist.")

		if not os.path.isdir(backup_location):
			raise NotADirectoryError(f"The directory {backup_location} does not exist.")

		file_name: str = os.path.basename(file_path)
		name, ext = os.path.splitext(file_name)
		date_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
		backup_file_name = f"{name}_{date_time_str}{ext}"
		backup_path = os.path.join(backup_location, backup_file_name)

		shutil.copy2(file_path, backup_path)
		print(f"File copied to {backup_path}")

	@staticmethod
	def get_temp_dir() -> str:
		temp_dir: str = os.getenv('TMPDIR') or os.getenv('TEMP') or os.getenv('TMP') or '/tmp'
		if not os.path.exists(temp_dir):
			temp_dir = '/tmp'
		if not os.path.exists(temp_dir):
			raise ValueError("Cannot determine the temporary directory.")
		return temp_dir

	@staticmethod
	def get_stable_temp_file_path(prefix: str, unique_id: str, extension: str) -> str:
		temp_dir: str = FilePathTools.get_temp_dir()

		if not unique_id:
			raise ValueError("unique_id is required.")
		
		if not extension:
			raise ValueError("extension is required.")

		if not extension.startswith('.'):
			extension = '.' + extension

		unique_hash = hashlib.md5((prefix + unique_id).encode()).hexdigest()
		stable_filename = f"{prefix}_{unique_hash}{extension}"
		temp_file_path = os.path.join(temp_dir, stable_filename)

		return temp_file_path

	@staticmethod
	def get_unique_temp_file_path(prefix: str, extension: str) -> str:
		temp_dir: str = FilePathTools.get_temp_dir()

		if not extension.startswith('.'):
			extension = '.' + extension

		unique_filename = f"{prefix}_{os.getpid()}_{os.urandom(8).hex()}{extension}"
		temp_file_path = os.path.join(temp_dir, unique_filename)

		return temp_file_path

if __name__ == "__main__":
	import sys

	def _test():
		print("Running tests...")
		temp_dir = FilePathTools.get_temp_dir()
		print(f"Temp directory: {temp_dir}")

		temp_file_path = FilePathTools.get_unique_temp_file_path("test", ".txt")
		print(f"Unique temp file path: {temp_file_path}")

		stable_temp_file_path = FilePathTools.get_stable_temp_file_path("test", "unique_id", ".txt")
		print(f"Stable temp file path: {stable_temp_file_path}")

		FilePathTools.create_directory_if_not_exists("test_directory")
		print("Tests complete.")

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
