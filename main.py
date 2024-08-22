#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from dotenv import load_dotenv

from collect.logging_config import setup_logging
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
		refresh_time=4 * 60 * 60
	)
	ebay_auctions.load_auctions()

	collectbot.write_html_to_file(ebay_auctions=ebay_auctions)
	collectbot.create_sitemap(["https://hobbyreport.net"])
	collectbot.create_style_sheet()
	#collectbot.create_js()
	collectbot.backup_files()
	collectbot.update_edition()
	collectbot.upload_to_s3()
