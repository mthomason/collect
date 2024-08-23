#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
from dotenv import load_dotenv
from os import path

from core.logging_config import setup_logging
from collect.ebayapi import EBayAuctions
from collect.collectbot import CollectBot

if __name__ == "__main__":

	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

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
		refresh_time=4 * 60 * 60,
		user_agent=collectbot.user_agent
	)
	ebay_auctions.load_auctions()
	collectbot.set_ebay_auctions(ebay_auctions)
	collectbot.generate_site()
