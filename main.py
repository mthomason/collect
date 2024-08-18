#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
import markdown
import logging

from dotenv import load_dotenv

from os import path
from io import StringIO

from collect.logging_config import setup_logging
from collect.ebayapi import EBayAuctions
from collect.html_template_processor import HtmlTemplateProcessor
from collect.collectbot import CollectBot, CollectBotTemplate

if __name__ == "__main__":

	setup_logging("log/collectbot.log")
	logger = logging.getLogger(__name__)
	logger.info('Application started')

	collectbot: CollectBot = CollectBot()
	collectbotTemplate: CollectBotTemplate = CollectBotTemplate()

	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	app_id: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")
	app_name: str = "Hobby Report"

	extensions: list[str] = ['attr_list']
	bufhtml: StringIO = StringIO(initial_value="")

	# Initialize the eBay API tools
	ebay_auctions: EBayAuctions = EBayAuctions(
		filepath_cache_directory=collectbot.filepath_cache_directory,
		filepath_image_directory=collectbot.filepath_image_directory,
		refresh_time=4 * 60 * 60
	)
	ebay_auctions.load_auctions()
	topitem: dict[str, any] = ebay_auctions.most_watched()
	top_item_md: str = ebay_auctions.top_item_to_markdown(
		topitem,
		epn_category=collectbot.epn_category_headline_link
	)

	# Write the HTML header, nameplate, and lead headline
	bufhtml.write(CollectBotTemplate.generate_html_header())

	bufbody: StringIO = StringIO()
	bufbody.write(CollectBotTemplate.make_nameplate(app_name))
	bufbody.write(
		CollectBotTemplate.make_lead_headline(
			markdown.markdown(top_item_md, extensions=extensions)
		)
	)
	bufbody.write(
		CollectBotTemplate.auctions_to_html(ebay_auctions, exclude=[topitem['itemId']])
	)

	buffer_html_news: StringIO = StringIO()
	buffer_html_news.write(CollectBotTemplate.make_section_header("News"))
	buffer_html_news.write(collectbot.section_news_to_html())
	bufbody.write(CollectBotTemplate.make_news(buffer_html_news.getvalue()))
	buffer_html_news.close()
	bufhtml.write(CollectBotTemplate.make_newspaper(bufbody.getvalue()))


	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		bufhtml.write("\n")
		bufhtml.write(file.read())

	#Write to file named index.html
	with open(collectbot.filepath_output_html, 'w', encoding="utf-8") as file:
		file.write(bufhtml.getvalue())
		logger.info(f"File {collectbot.filepath_output_html} created.")

	filepath_output:str = path.join(collectbot.filepath_output_directory, "sitemap.xml")
	with open(filepath_output, 'w', encoding="utf-8") as file:
		file.write(collectbotTemplate.create_sitemap(["https://hobbyreport.net"]))
		logger.info(f"File {filepath_output} created.")

	#Backup the file
	collectbot.backup_files()
	logger.info(f"File {collectbot.filename_output} moved to backup.")

	#Minify the CSS
	with open("templates/style.css", "r") as file:
		style_content: str = HtmlTemplateProcessor.minify_css(file.read())
		with open("httpd/style.css", "w") as file:
			file.write(style_content)
			logger.info(f"File httpd/style.css created.")

	#collectbot.update_edition()
	logger.info(f"Edition updated to {collectbot.edition}.")

	#Upload to S3
	#collectbot.upload_to_s3()
	logger.info(f"Files uploaded to AWS S3.")
