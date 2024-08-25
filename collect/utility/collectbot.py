#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from io import StringIO
import json
import logging
import markdown
from random import randint

from os import path

from typing import Optional
from .core.html_template_processor import HtmlTemplateProcessor
from .core.rss_tool import RssTool
from .aws_helper import AwsCFHelper, AwsS3Helper
from .collectbot_template import CollectBotTemplate
from .ebayapi import EBayAuctions, AuctionListing
from .filepathtools import FilePathTools
from .listitem import TimeItem, IntItem, UnorderedList
from .listitem import UnorderedList, TimeItem, IntItem, StrItem, LinkItem, DescriptionList

logger = logging.getLogger(__name__)

class CollectBot:
	"""This is the main class for the CollectBot."""
	def __init__(
			self,
			app_name: str,
			app_config: dict[str, any],
			ebay_auctions: Optional[EBayAuctions] = None):
		assert app_name, "App name is required."
		assert app_config, "App config is required."
		self.collectbot_template: CollectBotTemplate = CollectBotTemplate()
		self._config: dict[str, any] = {}
		self._markdown_extensions: list[str] = ['attr_list']
		self._app_name: str = app_name
		self._ebay_auctions: EBayAuctions = ebay_auctions
		self._config = app_config
		with open("config/epn-categories.json", "r") as file:
			self._epn_categories = json.load(file)

	@property
	def filepath_log(self) -> str:
		return self._config["output-log-file"]

	@property
	def user_agent(self) -> str:
		"""Returns the user agent for the CollectBot."""
		user_agent: tuple[str, str] = (
			self._config["user-agent-name"],
			self._config["user-agent-version"]
		)
		return "/".join(user_agent)

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
		return datetime.fromisoformat(self._config["last-modified"])

	@property
	def filename_output(self) -> str:
		"""Returns the output file name."""
		return self._config["output-file-name"]

	@property
	def filepath_template_directory(self) -> str:
		"""Returns the directory path for the templates."""
		return self._config["directory-template"]

	@property
	def filepath_output_directory(self) -> str:
		"""Returns the directory path for the output."""
		return self._config["directory-out"]

	@property
	def filepath_image_directory(self) -> str:
		"""Returns the directory path for the images."""
		return self._config["directory-images"]

	@property
	def filepath_cache_directory(self) -> str:
		"""Returns the directory path for the cache."""
		return self._config["directory-cache"]
	
	@property
	def filepath_config_directory(self) -> str:
		"""Returns the directory path for the config."""
		return self._config["directory-config"]
	
	@property
	def epn_category_default(self) -> str:
		"""Returns the default category for the eBay Partner Network."""
		return self._epn_categories["default"]
	
	@property
	def epn_category_above_headline_link(self) -> str:
		"""Returns the category for the eBay Partner Network above the headline link."""
		return self._epn_categories["above_headline_link"]

	@property
	def epn_category_headline_link(self) -> str:
		"""Returns the category for the eBay Partner Network for the headline link."""
		return self._epn_categories["headline_link"]
	
	def write_html_to_file(self):
		"""Writes the HTML to the output file."""
		s: str = self.create_html()
		with open(self.filepath_output_html, 'w', encoding="utf-8") as file:
			file.write(s)
			logger.info(f"File {self.filepath_output_html} created.")

	def create_html(self) -> str:
		_header: str = self._create_html_header()
		_body: str = self._create_html_body()
		_footer: str = self._create_html_footer()
		return "".join((_header, _body, _footer))
	
	def _create_html_header(self) -> str:
		return CollectBotTemplate.create_html_header(self.filepath_template_directory)
	
	def _create_html_body(self) -> str:

		exclude: list[str] = [] # Track items displayed above the fold

		# Get the top 3-5 items to display above the fold
		topn: list[dict[str, any]] = self._ebay_auctions.top_n_sorted_auctions(
			randint(3, 5) + 1,
			exclude=exclude
		)

		# The top item will be used as a headline
		topitem: dict[str, any] = topn.pop(0)
		exclude.append(topitem['itemId'])

		above_fold_links: list[AuctionListing] = []
		for item in topn:
			listing: AuctionListing = self._ebay_auctions.top_item_to_markdown(
				item,
				epn_category=self.epn_category_above_headline_link,
				download_images=False
			)
			above_fold_links.append(listing)
			exclude.append(item['itemId'])

		top_listing: AuctionListing = self._ebay_auctions.top_item_to_markdown(
			topitem,
			epn_category=self.epn_category_headline_link
		)

		img: str = CollectBotTemplate.make_featured_image(
			top_listing.image,
			"Featured Auction"
		)

		attribs: dict[str, str] = { "href": top_listing.url }
		if top_listing.ending_soon:
			attribs["class"] = "thending"
		else:
			attribs["class"] = "th"

		title: str = CollectBotTemplate.strip_outter_tag(
			markdown.markdown(top_listing.title)
		)
		link: str = CollectBotTemplate.html_wrapper(
			tag="a", content=title, attributes=attribs
		)
		link = CollectBotTemplate.html_wrapper(tag="p", content=link)

		top_item_md: str = "\n".join((img, link))

		bufbody: StringIO = StringIO()
		bufbody.write(
			CollectBotTemplate.make_above_fold(
				self._config["display-above-the-fold-header"],
				above_fold_links
			)
		)
		bufbody.write(CollectBotTemplate.make_nameplate(self._app_name))
		bufbody.write(
			CollectBotTemplate.make_lead_headline(
				self._config["display-lead-headline-header"],
				body=top_item_md
			)
		)
		auctions: str = CollectBotTemplate.auctions_to_html(
			self._ebay_auctions, exclude=exclude
		) 

		buffer_html_news: StringIO = StringIO()
		buffer_html_news.write(CollectBotTemplate.make_section_header("News"))
		buffer_html_news.write(self.section_news_to_html())
		news: str = CollectBotTemplate.make_news(buffer_html_news.getvalue())
		bufbody.write(auctions)
		bufbody.write("\n")
		bufbody.write(news)
		result: str = CollectBotTemplate.make_newspaper(bufbody.getvalue())
		buffer_html_news.close()
		bufbody.close()
		topn.clear()
		return result

	def _create_html_footer(self) -> str:
		item_s = StrItem(title="Site", value="Hobby Report")
		item_l = StrItem(title="Link", value="https://hobbyreport.net")
		item_e = IntItem(title="Edition", value=self.edition)
		item_u = TimeItem(title="Last Updated", value=datetime.now())
		dlitems = DescriptionList()
		dlitems.additem(item_s)
		dlitems.additem(item_l)
		dlitems.additem(item_e)
		dlitems.additem(item_u)
		footer_html: str = CollectBotTemplate.make_footer(title="Links", items=dlitems)
		
		end_html: str = CollectBotTemplate.create_html_end(
			self.filepath_template_directory
		)
		return footer_html + end_html

	def create_sitemap(self, urls: list[str]):
		filepath_output:str = path.join(self.filepath_output_directory, "sitemap.xml")
		with open(filepath_output, 'w', encoding="utf-8") as file:
			file.write(self.collectbot_template.create_sitemap(urls))
			logger.info(f"File {filepath_output} created.")

	def create_style_sheet(self):
		"""Creates the style sheet for the CollectBot."""
		filepath_input: str = path.join(self.filepath_template_directory, "style.css")
		with open(filepath_input, "r") as file:
			style_content: str = HtmlTemplateProcessor.minify_css(file.read())
			filepath_output: str = path.join(self.filepath_output_directory, "style.css")
			with open(filepath_output, "w") as file:
				file.write(style_content)
				logger.info(f"File {filepath_output} created.")
	
	def create_js(self):
		"""Creates the JavaScript file for the CollectBot."""
		filepath_input: str = path.join(self.filepath_template_directory, "h.min.js")
		with open(filepath_input, "r") as fin:
			filepath_output: str = path.join(self.filepath_output_directory, "h.min.js")
			with open(filepath_output, "w") as fout:
				fout.write(fin.read())
				logger.info(f"File {filepath_output} created.")

	def update_edition(self):
		"""Updates the edition of the CollectBot."""
		self._config["edition"] = self._config["edition"] + 1
		self._config["last-modified"] = datetime.now(timezone.utc).isoformat()
		filepath_config: str = path.join(
			self.filepath_config_directory,
			"config.json"
		)
		with open(filepath_config, "w") as file:
			json.dump(self._config, file, indent="\t")

	def section_news(self, title: str, urls:list[dict[str, any]],
					 interval: int, filename: str,
					 max_results: int = 10) -> str:
		rss: RssTool = RssTool(self.user_agent,
							   urls=urls, cache_duration=interval,
							   max_results=max_results,
							   cache_directory=self.filepath_cache_directory,
							   cache_file=filename)
		html_section: str = CollectBotTemplate.generate_html_section(
			title=title,
			fetch_func=rss.fetch
		)
		return html_section
	
	def section_news_to_html(self) -> str:
		p: str = path.join(self.filepath_config_directory, "rss-feeds.json")
		buff: StringIO = StringIO()
		with open(p, "r") as f:
			rss_feeds = json.load(f)
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
		aws_helper: AwsS3Helper = AwsS3Helper(
			bucket_name=self._config['aws-s3-bucket-name'],
			region=self._config['aws-s3-region'],
			ensure_bucket=bool(self._config['aws-s3-ensure-bucket']),
			cache_dir=self.filepath_cache_directory
		)

		img_filepath: str = path.join(self.filepath_template_directory, "og-image.jpeg")
		og_image_updated: bool = aws_helper.upload_file_if_changed(
			file_path=img_filepath, object_name="og-image.jpeg"
		)

		index_updated: bool = aws_helper.upload_file_if_changed(
			file_path='httpd/index.html', object_name='index.html'
		)
		sitemap_updated: bool = aws_helper.upload_file_if_changed(
			file_path='httpd/sitemap.xml', object_name='sitemap.xml'
		)
		style_updated: bool = aws_helper.upload_file_if_changed(
			file_path='httpd/style.css', object_name='style.css'
		)
		favicon_updated: bool = aws_helper.upload_file_if_changed(
			file_path='httpd/favicon.ico', object_name='favicon.ico'
		)
		robots_updated: bool = aws_helper.upload_file_if_changed(
			file_path='httpd/robots.txt', object_name='robots.txt'
		)
		js_updated: bool = aws_helper.upload_file_if_changed(
			file_path="httpd/h.min.js", object_name="h.min.js"
		)

		if index_updated or sitemap_updated or style_updated or favicon_updated or robots_updated or js_updated:
			cf: AwsCFHelper = AwsCFHelper()
			if index_updated:
				invalidation_id = cf.create_invalidation(['/'])
				logger.info(f"Invalidation ID: {invalidation_id} - /")

				invalidation_id = cf.create_invalidation(['/index.html'])
				logger.info(f"Invalidation ID: {invalidation_id} - /index.html")

			#if js_updated:
			#	invalidation_id = cf.create_invalidation(['/display.js'])
			#	logger.info(f"Invalidation ID: {invalidation_id}")

			if sitemap_updated:
				invalidation_id = cf.create_invalidation(['/sitemap.xml'])
				logger.info(f"Invalidation ID: {invalidation_id} - /sitemap.xml")

			if style_updated:
				invalidation_id = cf.create_invalidation(['/style.css'])
				logger.info(f"Invalidation ID: {invalidation_id} - /style.css")

			if js_updated:
				invalidation_id = cf.create_invalidation(['/h.min.js'])
				logger.info(f"Invalidation ID: {invalidation_id} - /h.min.js")

			if favicon_updated:
				invalidation_id = cf.create_invalidation(['/favicon.ico'])
				logger.info(f"Invalidation ID: {invalidation_id} - /favicon.ico")
		
			if robots_updated:
				invalidation_id = cf.create_invalidation(['/robots.txt'])
				logger.info(f"Invalidation ID: {invalidation_id} - /robots.txt")

	def set_ebay_auctions(self, ebay_auctions: EBayAuctions):
		self._ebay_auctions = ebay_auctions

	def generate_site(self):
		self.write_html_to_file()
		self.create_sitemap(["https://hobbyreport.net"])
		self.create_style_sheet()
		self.create_js()
		self.backup_files()
		self.update_edition()
		self.upload_to_s3()
		logger.info("Site generation complete.")
