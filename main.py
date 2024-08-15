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
from collect.ebayapi import eBayAPI
from collect.promptchat import PromptPersonalityAuctioneer
from collect.rss_tool import RssTool
from collect.aws_helper import AwsS3Helper
from collect.aws_helper import AwsCFHelper

class BaseTemplate:
	def __init__(self, adorner):
		self._adorner = adorner

	def md_convert(self, text: str) -> str:
		return markdown.markdown(text, extensions=['attr_list'])

	def md_adornment(self, adornment: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
		return self._adorner.md_adornment(adornment)
	
	def html_wrapper_attributes(self, tag: str, attributes: dict) -> Callable:
		def decorator(func: Callable[[str], str]) -> Callable[[str], str]:
			def wrapper(s: str) -> str:
				attrs = " ".join([f'{k}="{v}"' for k, v in attributes.items()])
				return f'<{tag} {attrs}>{func(s)}</{tag}>'
			return wrapper
		return decorator
	
	def html_wrapper(tag: str, content: str, attributes: dict = None) -> str:
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs}>{content}</{tag}>'

	def wrap_with_tag(self, tag: str, attributes: dict = None):
		def decorator(func: Callable[[str], str]) -> Callable[[str], str]:
			def wrapper(s: str) -> str:
				return self.html_wrapper(tag, func(s), attributes)
			return wrapper
		return decorator

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

	@_adorner.html_wrapper_attributes("div", {"class": "header-auctions"})
	def make_section_header_auctions(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "header-news"})
	def make_section_header_news(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("h1", {"class": "h1"})
	def make_h1(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("h2", {"class": "h2"})
	def make_h2(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("h3", {"class": "h3"})
	def make_h3(s: str) -> str: return s

class EBayAPITools:
	def __init__(self, cache_dir: str = "cache", image_dir: str = "httpd/i"):
		self._ebay_api: eBayAPI = eBayAPI()
		self._api_cache: APICache = APICache(cache_dir)
		self._image_dir: str = image_dir

	def search_top_items_from_catagory(self, category_id: str, ttl: int, max_results: int) -> list[dict[str, any]]:
		self._api_cache.cache_file = str.join(".", [str.zfill(category_id, 6), "json"])	
		search_results: list[dict[str, any]] = self._api_cache.cached_api_call(self._ebay_api.search_top_watched_items, category_id, max_results)
		return search_results

	def top_item_to_html(self, item_id: str, items: list[dict[str, any]], epn_category: str) -> str:
		"""This is the most watched collectable item."""
		"""
			Items is a list of dictionaries with keys:
			- 'itemId': str
			- 'title': str
			- 'globalId': str
			- 'subtitle': str
			- 'primaryCategory': dict
			- 'galleryURL': str
			- 'viewItemURL': str
			- 'autoPay': bool
			- 'postalCode': str
			- 'location': str
			- 'country': str
			- 'shippingInfo': dict
			- 'sellingStatus': dict
			- 'listingInfo': dict
			- 'returnsAccepted': bool
			- 'condition': dict
			- 'isMultiVariationListing': bool
			- 'topRatedListing': bool
		"""
		item: dict[str, any] = None
		for item in items:
			if item['itemId'] == item_id:
				break

		if not item:
			raise ValueError("Item not found in the list.")

		"""Have the auctioneer generate a headline for the item."""
		auctioneer: PromptPersonalityAuctioneer = PromptPersonalityAuctioneer()
		auctioneer.add_headline(id=item_id, headline=item['title'])
		headlines_iterator = auctioneer.get_headlines()

		"""Get the first headline from the auctioneer.  There should only be one."""
		title: str = ""
		for headline in headlines_iterator:
			title = headline['headline']
			break

		buffer: StringIO = StringIO()
		item_url: str = item['viewItemURL']
		epn_url: str = eBayAPI.generate_epn_link(item_url, epn_category)
		end_time_string: str = item['listingInfo']['endTime']
		end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
		now: datetime = datetime.now(tz=end_datetime.tzinfo)

		image_url = item['galleryURL']
		image_url_large: str = ""

		if image_url.endswith("s-l140.jpg"):
			image_url = image_url.replace("s-l140.jpg", "s-l400.jpg")

		try:
			image_cache = ImageCache(url=image_url, identifier=item_id, cache_dir=self._image_dir)
		except Exception as e:
			image_cache = ImageCache(url=item['galleryURL'], identifier=item_id, cache_dir=self._image_dir)
			print(f"Error: {e}")

		try:
			if image_url.endswith("s-l400.jpg"):
				image_url_large = image_url.replace("s-l400.jpg", "s-l1600.jpg")
			image_cache_large = ImageCache(url=image_url_large, identifier=item_id + "_large", cache_dir=self._image_dir)
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


	def top_item_to_markdown(self, item_id: str, items: list[dict[str, any]], epn_category: str) -> str:
		"""This is the most watched collectable item."""
		"""
			Items is a list of dictionaries with keys:
			- 'itemId': str
			- 'title': str
			- 'globalId': str
			- 'subtitle': str
			- 'primaryCategory': dict
			- 'galleryURL': str
			- 'viewItemURL': str
			- 'autoPay': bool
			- 'postalCode': str
			- 'location': str
			- 'country': str
			- 'shippingInfo': dict
			- 'sellingStatus': dict
			- 'listingInfo': dict
			- 'returnsAccepted': bool
			- 'condition': dict
			- 'isMultiVariationListing': bool
			- 'topRatedListing': bool
		"""
		item: dict[str, any] = None
		for item in items:
			if item['itemId'] == item_id:
				break

		if not item:
			raise ValueError("Item not found in the list.")

		"""Have the auctioneer generate a headline for the item."""
		auctioneer: PromptPersonalityAuctioneer = PromptPersonalityAuctioneer()
		auctioneer.add_headline(id=item_id, headline=item['title'])
		headlines_iterator = auctioneer.get_headlines()

		"""Get the first headline from the auctioneer.  There should only be one."""
		title: str = ""
		for headline in headlines_iterator:
			title = headline['headline']
			break

		buffer: StringIO = StringIO()
		item_url: str = item['viewItemURL']
		epn_url: str = eBayAPI.generate_epn_link(item_url, epn_category)
		end_time_string: str = item['listingInfo']['endTime']
		end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
		now: datetime = datetime.now(tz=end_datetime.tzinfo)

		image_url = item['galleryURL']
		image_url_large: str = ""

		if image_url.endswith("s-l140.jpg"):
			image_url = image_url.replace("s-l140.jpg", "s-l400.jpg")

		try:
			image_cache = ImageCache(url=image_url, identifier=item_id, cache_dir=self._image_dir)
		except Exception as e:
			image_cache = ImageCache(url=item['galleryURL'], identifier=item_id, cache_dir=self._image_dir)
			print(f"Error: {e}")

		try:
			if image_url.endswith("s-l400.jpg"):
				image_url_large = image_url.replace("s-l400.jpg", "s-l1600.jpg")
			image_cache_large = ImageCache(url=image_url_large, identifier=item_id + "_large", cache_dir=self._image_dir)
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
	
	def get_top_item_id(search_results: list[dict[str, any]]) -> str:
		"""Returns the item_id of the most watched item in the list."""
		if not search_results:
			raise ValueError("search_results is required.")

		max_watch_count: int = 0
		max_item_id: str = ""

		for item in search_results:
			watch_count = item['listingInfo']['watchCount']
			watch_count_int: int = 0

			if type(watch_count) is str:
				watch_count_int = int(watch_count)
			else:
				watch_count_int = watch_count
		
			if watch_count_int > max_watch_count:
				max_watch_count = watch_count_int
				max_item_id = item['itemId']

		return max_item_id

	def search_results_to_markdown(self, items: list[dict], epn_category: str,
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
				epn_url = eBayAPI.generate_epn_link(item_url, epn_category)
				end_time_string: str = item['listingInfo']['endTime']
				end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
				now: datetime = datetime.now(tz=end_datetime.tzinfo)

				if end_datetime > now:

					if display_image and ctr == 0:
						image_url = item['galleryURL']

						buffer.write("![image](")
						buffer.write(image_url)
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

	def section_news(self, title: str, urls:list[dict[str, any]], interval: int, filename: str) -> str:
		rss_tool: RssTool = RssTool(urls=urls, cache_duration=interval,
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


		#invalidation_id = cf.create_invalidation(['/style.css'])
		#logger.info(f"Invalidation ID: {invalidation_id}")

'''
	Main function
'''
if __name__ == "__main__":

	# Setup logging
	setup_logging("log/collectbot.log")
	logger = logging.getLogger(__name__)
	logger.info('Application started')

	# Initialize the CollectBot and CollectBotTemplate
	collectbot: CollectBot = CollectBot()
	collectbotTemplate: CollectBotTemplate = CollectBotTemplate()

	# Program Initalization
	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	# Set Inital Values
	app_id: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")
	app_name: str = "Hobby Report"

	ebay_refresh_time: int = 4 * 60 * 60

	buffer_html: StringIO = StringIO(initial_value="")
	# Write the HTML header, nameplate, and lead headline
	with open('templates/header.html', 'r', encoding="utf-8") as input_file:
		buffer_html.write(input_file.read())
		
	buffer_html.write("\t<div id=\"newspaper\">\n")

	nameplate: str = CollectBotTemplate.make_h1(app_name)
	nameplate = CollectBotTemplate.make_nameplate(nameplate)

	buffer_html.write(nameplate)

	extensions: list[str] = ['attr_list']

	# Initialize the eBay API tools
	ebay_tools: EBayAPITools = EBayAPITools(cache_dir=collectbot.filepath_cache_directory, image_dir=collectbot.filepath_image_directory)

	buffer_html_auctions: StringIO = StringIO()

	with open("config/auctions-ebay.json", "r") as file:
		# Load the auctions
		auctions_ebay = json.load(file)

		# Generate the HTML for the lead headline
		lead_headline: str = ""
		all_items: list[dict[str, any]] = []
		for auction in auctions_ebay:
			items: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory(auction['id'], ttl=ebay_refresh_time, max_results=auction['count'])
			auction['items'] = items
			all_items.extend(items)

		top_item_id: str = EBayAPITools.get_top_item_id(all_items)

		top_item_md: str = ebay_tools.top_item_to_markdown(top_item_id, all_items, epn_category=collectbot.epn_category_headline_link)
		lead_headline = markdown.markdown(top_item_md, extensions=extensions)
		if not lead_headline:
			logger.error("lead_headline is required.")
			raise ValueError("lead_headline is required.")
		lead_headline = CollectBotTemplate.make_lead_headline(lead_headline)
		all_items.clear()

		# Write the lead headline
		buffer_html.write(lead_headline)

		section_header: str = CollectBotTemplate.make_h2("Auctions")
		section_header = CollectBotTemplate.make_section_header_auctions(section_header)
		buffer_html_auctions.write(section_header)

		buffer_html_sections: StringIO = StringIO()
		for auction in auctions_ebay:
			buffer_html_section: StringIO = StringIO()
			buffer_html_section.write(CollectBotTemplate.make_h3(auction['title']))
			items: list[dict[str, any]] = auction['items']
			search_result: str = ebay_tools.search_results_to_markdown(items=items, epn_category=auction['epn-category'], exclude=[top_item_id])
			search_result = collectbotTemplate._md.convert(search_result)
			search_result = CollectBotTemplate.make_content(search_result)
			buffer_html_section.write(search_result)
			
			buffer_html_sections.write(CollectBotTemplate.make_section(buffer_html_section.getvalue()))
			buffer_html_section.seek(0)
			buffer_html_section.truncate(0)

		
		buffer_html_auctions.write(CollectBotTemplate.make_container(buffer_html_sections.getvalue()))
		buffer_html.write(CollectBotTemplate.make_auctions(buffer_html_auctions.getvalue()))
		buffer_html.write("\n")



	buffer_html_auctions.seek(0)
	buffer_html_auctions.truncate(0)

	section_header = CollectBotTemplate.make_h2("News")
	section_header = CollectBotTemplate.make_section_header_news(section_header)
	buffer_html_auctions.write(section_header)

	buffer_html_auctions.write("<div class=\"container\">\n")

	with open("config/rss-feeds.json", "r") as file:
		rss_feeds = json.load(file)

	section_html: str = ""
	for feed in rss_feeds:
		section_html = collectbot.section_news(**feed)
		buffer_html_auctions.write(section_html)

	buffer_html_auctions.write("</div>\n") # Close the container div
	buffer_html_auctions.write("</div>\n") # Close the newspaper div

	buffer_html.write(CollectBotTemplate.make_news(buffer_html_auctions.getvalue()))

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		buffer_html.write("\n")
		buffer_html.write(file.read())

	#Write to file named index.html
	filepath_output: str = path.join(collectbot.filepath_output_directory, collectbot.filename_output)
	with open(filepath_output, 'w', encoding="utf-8") as file:
		file.write(buffer_html.getvalue())
		logger.info(f"File {filepath_output} created.")

	filepath_output:str = path.join(collectbot.filepath_output_directory, "sitemap.xml")
	with open(filepath_output, 'w', encoding="utf-8") as file:
		file.write(collectbotTemplate.create_sitemap(["https://hobbyreport.net"]))
		logger.info(f"File {filepath_output} created.")

	#Backup the file
	collectbot.backup_files()
	logger.info(f"File {collectbot.filename_output} moved to backup.")

	#Upload to S3
	collectbot.upload_to_s3()
	logger.info(f"Files uploaded to AWS S3.")
