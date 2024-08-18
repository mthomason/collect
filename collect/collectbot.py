#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from io import StringIO
import json
import logging
import markdown
import pprint

from os import path

from collect.aws_helper import AwsCFHelper, AwsS3Helper
from collect.collectbot_template import CollectBotTemplate
from collect.ebayapi import EBayAuctions
from collect.filepathtools import FilePathTools
from collect.html_template_processor import HtmlTemplateProcessor
from collect.rss_tool import RssTool

logger = logging.getLogger(__name__)

class CollectBot:
	"""This is the main class for the CollectBot."""
	def __init__(self, app_name: str = "Hobby Report"):
		"""_summary_
			Initializes the CollectBot.

			_config_
			{
				"directory-out": "httpd/",
				"directory-template": "template/",
				"directory-cache": "cache/",
				"directory-images: "cache/images/",
				"output-file-name": "index.html"
			}
		"""
		self.collectbot_template: CollectBotTemplate = CollectBotTemplate()
		self._config: dict[str, any] = {}
		self._markdown_extensions: list[str] = ['attr_list']
		self._app_name: str = app_name
		with open("config/config.json", "r") as file:
			self._config = json.load(file)
		with open("config/epn-categories.json", "r") as file:
			self._epn_categories = json.load(file)

	@property
	def filepath_log(self) -> str:
		return path.join(
			self._config["directory-log"],
			self._config["output-log-file"]
		)

	@property
	def filepath_output_html(self) -> str:
		return path.join(self.filepath_output_directory, self.filename_output)

	@property
	def edition(self) -> int:
		"""Returns the edition of the CollectBot."""
		return self._config['edition']
	
	@property
	def last_modified_text(self) -> str:
		"""Returns the last modified date of the CollectBot as a string."""
		utc_time = datetime.fromisoformat(self._config['last-modified'])
		local_offset = datetime.now().astimezone().utcoffset()
		local_time = utc_time + local_offset
		return local_time.strftime("%Y-%m-%d %I:%M %p")

	@property
	def last_modified(self) -> datetime:
		"""Returns the last modified date of the CollectBot."""
		return datetime.fromisoformat(self._config['last-modified'])

	@property
	def filename_output(self) -> str:
		"""Returns the output file name."""
		return self._config['output-file-name']

	@property
	def filepath_output_directory(self) -> str:
		"""Returns the directory path for the output."""
		return self._config['directory-out']

	@property
	def filepath_image_directory(self) -> str:
		"""Returns the directory path for the images."""
		return self._config['directory-images']

	@property
	def filepath_cache_directory(self) -> str:
		"""Returns the directory path for the cache."""
		return self._config['directory-cache']
	
	@property
	def epn_category_default(self) -> str:
		"""Returns the default category for the eBay Partner Network."""
		return self._epn_categories['default']
	
	@property
	def epn_category_above_headline_link(self) -> str:
		"""Returns the category for the eBay Partner Network above the headline link."""
		return self._epn_categories['above_headline_link']

	@property
	def epn_category_headline_link(self) -> str:
		"""Returns the category for the eBay Partner Network for the headline link."""
		return self._epn_categories['headline_link']
	
	def epn_category_id(self, category: str) -> str:
		"""Returns the eBay Partner Network category ID for the given category."""
		r: str = ""
		if category in self._epn_categories:
			r = self._epn_categories[category]
		else:
			r = self.epn_category_default
		return r

	def write_html_to_file(self, ebay_auctions: EBayAuctions):
		"""Writes the HTML to the output file."""
		s: str = self.create_html(ebay_auctions)
		with open(self.filepath_output_html, 'w', encoding="utf-8") as file:
			file.write(s)
			logger.info(f"File {self.filepath_output_html} created.")

	def create_html(self, ebay_auctions: EBayAuctions) -> str:
		_header: str = self._create_html_header()
		_body: str = self._create_html_body(ebay_auctions=ebay_auctions)
		_footer: str = self.create_html_footer()
		return "".join((_header, _body, _footer))
	
	def _create_html_header(self) -> str:
		return CollectBotTemplate.create_html_header()
	
	def _create_html_body(self, ebay_auctions: EBayAuctions) -> str:
		topitem: dict[str, any] = ebay_auctions.most_watched()
		top_item_md: str = ebay_auctions.top_item_to_markdown(
			topitem,
			epn_category=self.epn_category_headline_link
		)
		bufbody: StringIO = StringIO()
		bufbody.write(CollectBotTemplate.make_nameplate(self._app_name))
		bufbody.write(CollectBotTemplate.make_lead_headline(top_item_md))
		bufbody.write(CollectBotTemplate.auctions_to_html(ebay_auctions, exclude=[topitem['itemId']]))
		buffer_html_news: StringIO = StringIO()
		buffer_html_news.write(CollectBotTemplate.make_section_header("News"))
		buffer_html_news.write(self.section_news_to_html())
		bufbody.write(CollectBotTemplate.make_news(buffer_html_news.getvalue()))
		result: str = CollectBotTemplate.make_newspaper(bufbody.getvalue())
		buffer_html_news.close()
		bufbody.close()
		return result

	def create_html_footer(self) -> str:
		return CollectBotTemplate.create_html_footer()

	def create_sitemap(self, urls: list[str]):
		filepath_output:str = path.join(self.filepath_output_directory, "sitemap.xml")
		with open(filepath_output, 'w', encoding="utf-8") as file:
			file.write(self.collectbot_template.create_sitemap(urls))
			logger.info(f"File {filepath_output} created.")

	def create_style_sheet(self):
		"""Creates the style sheet for the CollectBot."""
		with open("templates/style.css", "r") as file:
			style_content: str = HtmlTemplateProcessor.minify_css(file.read())
			with open("httpd/style.css", "w") as file:
				file.write(style_content)
				logger.info("File httpd/style.css created.")

	def update_edition(self):
		"""Updates the edition of the CollectBot."""
		self._config["edition"] = self._config["edition"] + 1
		self._config["last-modified"] = datetime.now(timezone.utc).isoformat()
		with open("config/config.json", "w") as file:
			json.dump(self._config, file, indent="\t")

	def section_news(self, title: str, urls:list[dict[str, any]],
					 interval: int, filename: str,
					 max_results: int = 10) -> str:
		rss_tool: RssTool = RssTool(urls=urls, cache_duration=interval,
									max_results=max_results,
									cache_directory=self.filepath_cache_directory,
									cache_file=filename)
		html_section: str = CollectBotTemplate.generate_html_section(
			title=title,
			fetch_func=rss_tool.fetch
		)
		return html_section
	
	def section_news_to_html(self) -> str:
		buff: StringIO = StringIO()
		with open("config/rss-feeds.json", "r") as file:
			rss_feeds = json.load(file)
			section_html: str = ""
			for feed in rss_feeds:
				section_html = self.section_news(**feed)
				buff.write(section_html)

		return CollectBotTemplate.make_container(buff.getvalue())

	def backup_files(self):
		"""Backs up the output file."""
		FilePathTools.create_directory_if_not_exists("backup")
		FilePathTools.backup_file(self.filepath_output_html, "backup")
		logger.info(f"File {self.filename_output} moved to backup.")


	def upload_to_s3(self):
		"""Uploads the output file to S3."""
		aws_helper: AwsS3Helper = AwsS3Helper(bucket_name='hobbyreport.net', region='us-east-1')
		aws_helper.upload_images_with_tracking('httpd/i')
		aws_helper.upload_file(file_path='httpd/index.html', object_name='index.html')
		aws_helper.upload_file(file_path='httpd/sitemap.xml', object_name='sitemap.xml')
		aws_helper.upload_file(file_path='httpd/style.css', object_name='style.css')
		aws_helper.upload_file(file_path='httpd/favicon.ico', object_name='favicon.ico')
		aws_helper.upload_file(file_path='httpd/robots.txt', object_name='robots.txt')

		#Create an invalidation for the CloudFront distribution
		cf: AwsCFHelper = AwsCFHelper()

		invalidation_id = cf.create_invalidation(['/'])
		logger.info(f"Invalidation ID: {invalidation_id} - /")

		invalidation_id = cf.create_invalidation(['/index.html'])
		logger.info(f"Invalidation ID: {invalidation_id} - /index.html")

		invalidation_id = cf.create_invalidation(['/sitemap.xml'])
		logger.info(f"Invalidation ID: {invalidation_id} - /sitemap.xml")

		invalidation_id = cf.create_invalidation(['/style.css'])
		logger.info(f"Invalidation ID: {invalidation_id}")
