#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from dotenv import load_dotenv

from core.logging_config import setup_logging
from collect.ebayapi import EBayAuctions
from collect.collectbot import CollectBot

if __name__ == "__main__":

	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	collectbot: CollectBot = CollectBot()

	setup_logging(collectbot.filepath_log)
	logger = logging.getLogger(__name__)
	logger.info("Application started")

	ebay_auctions: EBayAuctions = EBayAuctions(
		filepath_cache_directory=collectbot.filepath_cache_directory,
		filepath_image_directory=collectbot.filepath_image_directory,
		filepath_config_directory=collectbot.filepath_config_directory,
		refresh_time=4 * 60 * 60,
		user_agent=collectbot.user_agent
	)
	ebay_auctions.load_auctions()
	collectbot.generate_site(ebay_auctions=ebay_auctions)
