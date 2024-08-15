# /collect/logging_config.py
# -*- coding: utf-8 -*-

import logging

def setup_logging(log_file_path: str, log_level: int = logging.INFO) -> None:
	logging.basicConfig(
		level=log_level,
		format="%(asctime)s %(name)s %(levelname)s: %(message)s",
		handlers=[
			logging.FileHandler(log_file_path),
			logging.StreamHandler()
		]
	)
