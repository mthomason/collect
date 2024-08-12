import logging

def setup_logging(log_file_path: str) -> None:
	logging.basicConfig(
		level=logging.DEBUG,
		format="%(asctime)s %(name)s %(levelname)s: %(message)s",
		handlers=[
			logging.FileHandler(log_file_path),
			logging.StreamHandler()
		]
	)
