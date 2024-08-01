# /collect/filepathtools.py
# -*- coding: utf-8 -*-

import os
import hashlib

class FilePathTools:
	def get_temp_dir() -> str:
		temp_dir: str = os.getenv('TMPDIR') or os.getenv('TEMP') or os.getenv('TMP') or '/tmp'
		if not os.path.exists(temp_dir):
			temp_dir = '/tmp'
		if not os.path.exists(temp_dir):
			raise ValueError("Cannot determine the temporary directory.")
		return temp_dir

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

	def get_unique_temp_file_path(prefix: str, extension: str) -> str:
		temp_dir: str = FilePathTools.get_temp_dir()

		if not extension.startswith('.'):
			extension = '.' + extension

		unique_filename = f"{prefix}_{os.getpid()}_{os.urandom(8).hex()}{extension}"
		temp_file_path = os.path.join(temp_dir, unique_filename)

		return temp_file_path

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
