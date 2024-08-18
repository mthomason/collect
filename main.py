# /main.py
# -*- coding: utf-8 -*-

import json
import uuid
import markdown
import logging

from random import randint
from dotenv import load_dotenv

from os import path
from pathlib import Path

from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Generator, Callable

from collect.logging_config import setup_logging
from collect.string_adorner import StringAdorner
from collect.filepathtools import FilePathTools
from collect.apicache import APICache
from collect.imagecache import ImageCache
from collect.ebayapi import eBayAPIHelper
from collect.promptchat import PromptPersonalityAuctioneer
from collect.rss_tool import RssTool
from collect.aws_helper import AwsS3Helper
from collect.aws_helper import AwsCFHelper
from collect.html_template_processor import HtmlTemplateProcessor

class CollectBotTemplate:
	_adorner = StringAdorner()

	def __init__(self):
		self._md = markdown.Markdown(extensions=['attr_list'])

	def create_sitemap(self, urls: list[str]) -> str:
		buffer: StringIO = StringIO()
		buffer.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
		buffer.write("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
		for url in urls:
			buffer.write("\t<url>\n")
			buffer.write(f"\t\t<loc>{url}</loc>\n")
			buffer.write("\t\t<lastmod>")
			buffer.write(datetime.now().astimezone(timezone.utc).isoformat(timespec='minutes'))
			buffer.write("</lastmod>\n")
			buffer.write("\t\t<changefreq>hourly</changefreq>\n")
			buffer.write("\t\t<priority>1.0</priority>\n")
			buffer.write("\t</url>\n")

		buffer.write("</urlset>\n")
		return buffer.getvalue()
	
	def html_wrapper(tag: str, content: str, attributes: dict = None) -> str:
		assert tag, "tag is required."
		assert content, "content is required."
		if not attributes:
			return f'<{tag}>{content}</{tag}>'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs}>{content}</{tag}>'

	def generate_html_section(title: str, fetch_func: Callable[[], Generator[dict[str, str], None, None]]) -> str:
		buffer_html: StringIO = StringIO()
		buffer_html.write("<div class=\"section\">\n")
		buffer_html.write(CollectBotTemplate.make_h3(title))
		buffer_html.write("\n<div class=\"content\">\n")
		buffer_html.write("<ul>\n")

		for item in fetch_func():
			link: str = CollectBotTemplate.html_wrapper("a", item['title'], {"href": item['link']})
			list_item: str = CollectBotTemplate.html_wrapper("li", link)
			buffer_html.write(list_item)
			buffer_html.write("\n")

		buffer_html.write("</ul>\n")
		buffer_html.write("</div>\n")
		buffer_html.write("</div>\n")

		return buffer_html.getvalue()

	@_adorner.md_adornment("**")
	def md_make_bold(s: str) -> str: return s
	
	@_adorner.html_wrapper_attributes("div", {"id": "nameplate"})
	@_adorner.html_wrapper_attributes("h1", {"class": "h1"})
	def make_nameplate(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"id": "lead-headline"})
	def make_lead_headline(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"id": "auctions"})
	def make_auctions(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"id": "news"})
	def make_news(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "container"})
	def make_container(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "section"})
	def make_section(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "content"})
	def make_content(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "section-header"})
	@_adorner.html_wrapper_attributes("h2", {"class": "h2"})
	def make_section_header(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "item-header"})
	@_adorner.html_wrapper_attributes("h1", {"class": "h3"})
	def make_item_header(s: str) -> str:
		return s

	@_adorner.html_wrapper_attributes("h1", {"class": "h1"})
	def make_h1(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("h2", {"class": "h2"})
	def make_h2(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("h3", {"class": "h3"})
	def make_h3(s: str) -> str: return s

class EBayAuctions:
	def __init__(self, filepath_cache_directory: str = "cache",
				 filepath_image_directory: str = "httpd/i"):
		self._ebay_api: eBayAPIHelper = eBayAPIHelper()
		self._api_cache: APICache = APICache(filepath_cache_directory)
		self._image_dir: str = filepath_image_directory

		with open("config/auctions-ebay.json", "r") as file:
			self._auctions: list[dict[str, any]] = json.load(file)

	@property
	def auctions(self) -> list[dict[str, any]]:
		return self._auctions

	def load_auctions(self):
		for auction in self._auctions:
			auction['items'] = self._search_top_items_from_catagory(
				auction['id'],
				ttl=ebay_refresh_time,
				max_results=auction['count']
			)
		return self._auctions
	
	def most_watched(self) -> dict[str, any]:
		return max(
			[item for cat in self._auctions for item in cat['items']],
			key=lambda x: int(x['listingInfo']['watchCount'])
		)
	
	def auctions_to_html(self, exclude: list[str]) -> str:
		bufauct: StringIO = StringIO()
		bufauct.write(CollectBotTemplate.make_section_header("Auctions"))

		bufsecs: StringIO = StringIO()
		for auction in self.auctions:

			bufsec: StringIO = StringIO()
			bufsec.write(CollectBotTemplate.make_item_header(auction['title']))
			html_: str = self._search_results_to_html(
				items=auction['items'],
				epn_category=auction['epn-category'],
				exclude=exclude)
			bufsec.write(CollectBotTemplate.make_content(html_))
			bufsecs.write(CollectBotTemplate.make_section(bufsec.getvalue()))
			bufsec.seek(0)
			bufsec.truncate(0)
			
		bufauct.write(CollectBotTemplate.make_container(bufsecs.getvalue()))
		return CollectBotTemplate.make_auctions(bufauct.getvalue())

	def _search_results_to_html(self, items: list[dict], epn_category: str,
							exclude:list[str] = None,
							display_image: bool = False) -> str:
		s: str = self._search_results_to_markdown(items, epn_category, exclude, display_image)
		return markdown.markdown(s, extensions=['attr_list'])

	def _search_top_items_from_catagory(self, category_id: str, ttl: int, max_results: int) -> list[dict[str, any]]:
		if not category_id or len(category_id) > 6:
			raise ValueError("category_id is required and must be less than six characters.")
		self._api_cache.cache_file = str.join(".", [str.zfill(category_id, 6), "json"])	
		search_results: list[dict[str, any]] = self._api_cache.cached_api_call(self._ebay_api.search_top_watched_items, category_id, max_results)
		return search_results

	def top_item_to_markdown(self, item: dict[str, any], epn_category: str) -> str:
		if not item:
			raise ValueError("Item not set.")

		"""Have the auctioneer generate a headline for the item."""
		auctioneer: PromptPersonalityAuctioneer = PromptPersonalityAuctioneer()
		auctioneer.add_headline(id=item['itemId'], headline=item['title'])
		headlines_iterator = auctioneer.get_headlines()

		"""Get the first headline from the auctioneer.  There should only be one."""
		title: str = ""
		for headline in headlines_iterator:
			title = headline['headline']
			break

		buffer: StringIO = StringIO()
		item_url: str = item['viewItemURL']
		epn_url: str = eBayAPIHelper.generate_epn_link(item_url, epn_category)
		end_time_string: str = item['listingInfo']['endTime']
		end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
		now: datetime = datetime.now(tz=end_datetime.tzinfo)

		image_url = item['galleryURL']
		image_url_large: str = ""

		if image_url.endswith("s-l140.jpg"):
			image_url = image_url.replace("s-l140.jpg", "s-l400.jpg")

		try:
			image_cache = ImageCache(url=image_url, identifier=item['itemId'], cache_dir=self._image_dir)
		except Exception as e:
			image_cache = ImageCache(url=item['galleryURL'], identifier=item['itemId'], cache_dir=self._image_dir)
			print(f"Error: {e}")

		try:
			if image_url.endswith("s-l400.jpg"):
				image_url_large = image_url.replace("s-l400.jpg", "s-l1600.jpg")
			image_cache_large = ImageCache(url=image_url_large, identifier=item['itemId'] + "_large", cache_dir=self._image_dir)
			local_path: str = image_cache_large.get_image_path()
			if image_cache_large._downloaded_image:
				aws_helper: AwsS3Helper = AwsS3Helper(bucket_name='hobbyreport.net', region='us-east-1')
				aws_helper.upload_images_with_tracking('httpd/i')

		except Exception as e:
			print(f"Error: {e}")

		local_path = image_cache.get_image_path()
		path_obj = Path(local_path)
		filename: str = path_obj.name
		new_path: str = str(Path('i') / filename)

		buffer.write("![image](")
		buffer.write(new_path)
		buffer.write("){: .th_img }\n\n")

		buffer.write("**[")
		buffer.write(title)
		buffer.write("](")
		buffer.write(epn_url)

		if end_datetime - now < timedelta(days=1):
			buffer.write("){: .th_ending }**\n\n")
		else:
			buffer.write("){: .th_ }**\n\n")

		return buffer.getvalue()

	def _search_results_to_markdown(self, items: list[dict], epn_category: str,
								exclude:list[str] = None,
								display_image: bool = False) -> str:
		"""Converts a list of search results to markdown."""
		buffer: StringIO = StringIO()
		if items:
			item: dict = None
			item_id: str = ""
			ctr: int = 0

			auctioneer: PromptPersonalityAuctioneer = PromptPersonalityAuctioneer()
			for item in items:
				item_id = item['itemId']
				if exclude and item_id in exclude:
					continue

				auctioneer.add_headline(id=item_id, headline=item['title'])

			headlines_ids: dict[str, str] = {}
			headlines_iterator = auctioneer.get_headlines()

			for headline in headlines_iterator:
				headlines_ids[headline['identifier']] = headline['headline']

			auctioneer.clear_headlines()

			for item in items:
				item_id = item['itemId']
				if exclude and item_id in exclude:
					continue
				"""_summary_
					Item has these properties, and more:
					- ['title']: str
					- ['listingInfo']['watchCount']: int
					- ['sellingStatus']['currentPrice']['value']: float
					- ['sellingStatus']['currentPrice']['_currencyId']: str
					- ['topRatedListing']: bool
				"""
				title = headlines_ids.get(item_id)
				if not title:
					title = item['title']

				item_url = item['viewItemURL']
				epn_url = eBayAPIHelper.generate_epn_link(item_url, epn_category)
				end_time_string: str = item['listingInfo']['endTime']
				end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
				now: datetime = datetime.now(tz=end_datetime.tzinfo)

				if end_datetime > now:
					if display_image and ctr == 0:
						buffer.write("![image](")
						buffer.write(item['galleryURL'])
						buffer.write(")\n\n")

					buffer.write(" * [")
					buffer.write(title)
					buffer.write("](")
					buffer.write(epn_url)

					if end_datetime - now < timedelta(days=1):
						buffer.write("){: .a_ending}\n")
					else:
						buffer.write(")\n")

					ctr += 1

		return buffer.getvalue()


class CollectBot:
	"""This is the main class for the CollectBot."""
	def __init__(self):
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
		self._config: dict[str, any] = {}
		with open("config/config.json", "r") as file:
			self._config = json.load(file)
		with open("config/epn-categories.json", "r") as file:
			self._epn_categories = json.load(file)

	def update_edition(self):
		"""Updates the edition of the CollectBot."""
		self._config["edition"] = self._config["edition"] + 1
		self._config["last-modified"] = datetime.now(timezone.utc).isoformat()
		with open("config/config.json", "w") as file:
			json.dump(self._config, file, indent="\t")

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

	def backup_files(self):
		"""Backs up the output file."""
		FilePathTools.create_directory_if_not_exists("backup")
		FilePathTools.backup_file(filepath_output, "backup")

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
	ebay_refresh_time: int = 4 * 60 * 60

	extensions: list[str] = ['attr_list']
	bufhtml: StringIO = StringIO(initial_value="")

	# Write the HTML header, nameplate, and lead headline
	processor: HtmlTemplateProcessor = HtmlTemplateProcessor("templates/header.html")
	processor.replace_from_file("style_inline", "templates/style_inline.css")
	bufhtml.write(processor.get_content())
	bufhtml.write("\t<div id=\"newspaper\">\n")

	# Write Site Nameplate
	bufhtml.write(CollectBotTemplate.make_nameplate(app_name))

	# Initialize the eBay API tools
	ebay_auctions: EBayAuctions = EBayAuctions(
		filepath_cache_directory=collectbot.filepath_cache_directory,
		filepath_image_directory=collectbot.filepath_image_directory
	)
	ebay_auctions.load_auctions()

	# Get the top item
	topitem: dict[str, any] = ebay_auctions.most_watched()
	top_item_id: str = topitem['itemId']

	top_item_md: str = ebay_auctions.top_item_to_markdown(
		topitem,
		epn_category=collectbot.epn_category_headline_link
	)
		
	lead_headline: str = markdown.markdown(top_item_md, extensions=extensions)
	if not lead_headline:
		logger.error("lead_headline is required.")
		raise ValueError("lead_headline is required.")

	lead_headline = CollectBotTemplate.make_lead_headline(lead_headline)

	# Write the lead headline
	bufhtml.write(lead_headline)
	bufhtml.write(ebay_auctions.auctions_to_html(exclude=[top_item_id]))

	buffer_html_news: StringIO = StringIO()
	buffer_html_news.write(CollectBotTemplate.make_section_header("News"))
	buffer_html_news.write("<div class=\"container\">\n")

	with open("config/rss-feeds.json", "r") as file:
		rss_feeds = json.load(file)
		section_html: str = ""
		for feed in rss_feeds:
			section_html = collectbot.section_news(**feed)
			buffer_html_news.write(section_html)

	buffer_html_news.write("</div>\n") # Close the container div

	buffer_html_news.write("</div>\n") # Close the newspaper div

	bufhtml.write(CollectBotTemplate.make_news(buffer_html_news.getvalue()))

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		bufhtml.write("\n")
		bufhtml.write(file.read())

	#Write to file named index.html
	filepath_output: str = path.join(collectbot.filepath_output_directory, collectbot.filename_output)
	with open(filepath_output, 'w', encoding="utf-8") as file:
		file.write(bufhtml.getvalue())
		logger.info(f"File {filepath_output} created.")

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
	#logger.info(f"Files uploaded to AWS S3.")
