#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import os
#import argparse
from dotenv import load_dotenv
from os import path
from collect.utility.core.logging_config import setup_logging
from collect.utility.ebayapi import EBayAuctions
from collect.utility.collectbot import CollectBot
from collect.utility.formatted_prompt import PromptPersonalityFunctional, GptFunctionPrompt

def main() -> int:

	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	"""

	with open("prompts/function_obtain_identity.json", "r") as file:
		function_def = json.load(file)

	fp: GptFunctionPrompt = GptFunctionPrompt.from_dict(function_def)
	ppf: PromptPersonalityFunctional = PromptPersonalityFunctional(
		apikey=os.getenv("OPENAI_API_KEY"),
		prompt=fp
	)

	ppf.add_prompt_item_data(
		("id-1", "2023-2024 Topps Chrome Basketball On-Card Auto Victor Wembanyama Black #7/10!"),
		("id-2", "2018 Bowman Chrome Shohei Ohtani Rookie Card #SO - PSA 10 Autograph"),
		("id-3", "Steph Curry, LeBron James, and Kevin Durant - 2024 Topps Now Olympic Sealed Pack 1/1"),
	)

	results: list[dict[str, str]] = ppf.get_results()
	for result in results:
		for key, value in result.items():
			print(f"{key}: {value}")


	"""

	#parser = argparse.ArgumentParser(
	#	prog='collectbot',
	#	usage='%(prog)s [options] path',
	#	description="Run collectbot with various options."
	#)

	#parser.add_argument(
	#	'--dry-run', 
	#	action='store_true', 
	#	help='A dry run of the program.  This will not conenct to the internet.'
	#)

	#args = parser.parse_args()
	#print(args.accumulate(args.integers))
	#exit(0)

	app_config: dict[str, any] = None
	with open("config/config.json", "r") as file:
		app_config = json.load(file)

	setup_logging(app_config["output-log-file"], log_level=logging.INFO)
	logger = logging.getLogger(__name__)
	logger.info("Application started")

	collectbot: CollectBot = CollectBot("Hobby Report", app_config)
	ebay_auctions: EBayAuctions = EBayAuctions(
		filepath_cache_directory=collectbot.filepath_cache_directory,
		filepath_image_directory=collectbot.filepath_image_directory,
		filepath_config_directory=collectbot.filepath_config_directory,
		refresh_time=collectbot._config["ebay-refresh-time"],
		user_agent=collectbot.user_agent
	)
	ebay_auctions.load_auctions()
	collectbot.set_ebay_auctions(ebay_auctions)
	collectbot.generate_site()

	return 0

if __name__ == "__main__":
	exit_code: int = main()
	exit(exit_code)
