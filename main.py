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

from datetime import datetime, timedelta
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

class CollectBotTemplate:
	_adorner: StringAdorner = StringAdorner()
	_md: markdown.Markdown = markdown.Markdown(extensions=['attr_list'])

	def generate_html_section(title: str, extensions: list[str], fetch_func: Callable[[], Generator[dict[str, str], None, None]]):
		buffer_html: StringIO = StringIO()
		buffer_html.write("<div class=\"section\">\n")
		buffer_html.write(CollectBotTemplate.make_h3(title))
		buffer_html.write("\n<div class=\"content\">\n")

		buffer_md: StringIO = StringIO()
		for item in fetch_func():
			buffer_md.write(" * [")
			buffer_md.write(item['title'])
			buffer_md.write("](")
			buffer_md.write(item['link'])
			buffer_md.write(")\n")

		buffer_html.write(CollectBotTemplate._md.convert(buffer_md.getvalue()))
		buffer_html.write("</div>\n</div>\n")
		buffer_md.close()

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
		return self._epn_categories[category]

'''
	Main function
'''
if __name__ == "__main__":
	setup_logging("log/collectbot.log")
	logger = logging.getLogger(__name__)
	logger.info('Application started')

	collectbot: CollectBot = CollectBot()
	collectbotTemplate: CollectBotTemplate = CollectBotTemplate()

	# Program Initalization
	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	# Set Inital Values
	app_id: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")
	app_name: str = "Hobby Report"

	refresh_time: int = 8 * 60 * 60

	buffer_html: StringIO = StringIO(initial_value="")
	extensions: list[str] = ['attr_list']

	# Initialize the eBay API tools
	ebay_tools: EBayAPITools = EBayAPITools(cache_dir=collectbot.filepath_cache_directory, image_dir=collectbot.filepath_image_directory)
	items_trading_cards: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("212", ttl=refresh_time, max_results=20)
	items_non_sports: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("183050", ttl=refresh_time, max_results=20)
	items_comics: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("259104", ttl=refresh_time, max_results=10)
	items_fossles: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("3213", ttl=refresh_time, max_results=6)
	items_coins: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("253", ttl=refresh_time, max_results=6)
	items_bobbleheads: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("149372", ttl=refresh_time, max_results=6)
	items_autographs: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("14429", ttl=refresh_time, max_results=6)
	items_military_relics: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("13956", ttl=refresh_time, max_results=6)
	items_stamps: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("260", ttl=refresh_time, max_results=6)
	items_antiques: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("20081", ttl=refresh_time, max_results=6)
	items_art: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("550", ttl=refresh_time, max_results=6)
	items_toys_hobbies: list[dict[str, any]] = ebay_tools.search_top_items_from_catagory("220", ttl=refresh_time, max_results=6)

	all_items: list[dict[str, any]] = items_trading_cards.copy()
	all_items.extend(items_non_sports)
	all_items.extend(items_comics)
	all_items.extend(items_fossles)
	all_items.extend(items_coins)
	all_items.extend(items_bobbleheads)
	all_items.extend(items_autographs)
	all_items.extend(items_military_relics)
	all_items.extend(items_stamps)
	all_items.extend(items_antiques)
	all_items.extend(items_art)
	all_items.extend(items_toys_hobbies)

	# Write the HTML header
	with open('templates/header.html', 'r', encoding="utf-8") as input_file:
		buffer_html.write(input_file.read())

	buffer_html.write("\t<div id=\"newspaper\">\n")

	nameplate: str = CollectBotTemplate.make_h1(app_name)
	nameplate = CollectBotTemplate.make_nameplate(nameplate)
	buffer_html.write(nameplate)

	top_item_id: str = EBayAPITools.get_top_item_id(all_items)
	top_item_md: str = ebay_tools.top_item_to_markdown(top_item_id, all_items, epn_category=collectbot.epn_category_headline_link)
	lead_headline: str = markdown.markdown(top_item_md, extensions=extensions)
	lead_headline = CollectBotTemplate.make_lead_headline(lead_headline)
	buffer_html.write(lead_headline)

	all_items.clear()

	buffer_html_auctions: StringIO = StringIO()
	section_header: str = CollectBotTemplate.make_h2("Auctions")
	section_header = CollectBotTemplate.make_section_header_auctions(section_header)
	buffer_html_auctions.write(section_header)

	sections: list[dict[str, object]] = [
			{"header": "Trading Cards", "items": items_trading_cards, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("trading_cards")},
			{"header": "Non Sports", "items": items_non_sports, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("non_sports")},
			{"header": "Comics", "items": items_comics, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("comics")},
			{"header": "Rocks and Fossils", "items": items_fossles, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("rocks_and_fossils")},
			{"header": "Autographs", "items": items_autographs, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("autographs")},
			{"header": "Coins", "items": items_coins, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("coins")},
			{"header": "Stamps", "items": items_stamps, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("stamps")},
			{"header": "Antiques", "items": items_antiques, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("antiques")},
			{"header": "Art", "items": items_art, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("art")},
			{"header": "Toys and Hobbies", "items": items_toys_hobbies, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("toys_and_hobbies")},
			{"header": "Military Relics", "items": items_military_relics, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("military_relics")},
			{"header": "Bobbleheads", "items": items_bobbleheads, "exclude": [top_item_id], "epn_category": collectbot.epn_category_id("bobbleheads")}
		]

	buffer_html_sections: StringIO = StringIO()
	for section in sections:
		buffer_html_section: StringIO = StringIO()
		buffer_html_section.write(CollectBotTemplate.make_h3(section['header']))
		md: str = ebay_tools.search_results_to_markdown(items=section['items'], epn_category=section['epn_category'], exclude=section['exclude'])
		md = CollectBotTemplate._md.convert(md)
		md = CollectBotTemplate.make_content(md)
		buffer_html_section.write(md)

		buffer_html_sections.write(CollectBotTemplate.make_section(buffer_html_section.getvalue()))
		buffer_html_section.seek(0)
		buffer_html_section.truncate(0)

	buffer_html_auctions.write(CollectBotTemplate.make_container(buffer_html_sections.getvalue()))
	buffer_html.write(CollectBotTemplate.make_auctions(buffer_html_auctions.getvalue()))
	
	buffer_html_auctions.seek(0)
	buffer_html_auctions.truncate(0)

	items_trading_cards.clear()
	items_non_sports.clear()
	items_comics.clear()
	items_fossles.clear()
	items_autographs.clear()
	items_bobbleheads.clear()
	items_military_relics.clear()
	items_coins.clear()
	items_stamps.clear()
	items_antiques.clear()
	items_art.clear()
	items_toys_hobbies.clear()

	section_header = CollectBotTemplate.make_h2("News")
	section_header = CollectBotTemplate.make_section_header_news(section_header)
	buffer_html_auctions.write(section_header)

	buffer_html_auctions.write("<div class=\"container\">\n")

	rss_tool: RssTool = RssTool(url="https://www.beckett.com/news/feed/",
							 cache_duration=60*30*3,
							 cache_directory=collectbot.filepath_cache_directory,
							 cache_file="rss_becket.json")
	html_section: str = CollectBotTemplate.generate_html_section(
		title="Releases",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	rss_tool = RssTool(urls=["https://robbreport.com/feed/"],
					cache_duration=60*60*2,
					cache_directory=collectbot.filepath_cache_directory,
					cache_file="rss_robbreport.json")
	
	html_section = CollectBotTemplate.generate_html_section(
		title="Luxury and Rare Items",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	# rss_tool = RssTool(urls=["https://retronauts.com/feed/rss"],
	# 				cache_duration=60*60*2,
	# 				cache_directory=collectbot.filepath_cache_directory,
	# 				cache_file="rss_retronauts.json")
	# html_section = CollectBotTemplate.generate_html_section(
	# 	title="Technology Collectibles",
	# 	extensions=extensions,
	# 	fetch_func=rss_tool.fetch
	# )
	buffer_html_auctions.write(html_section)

	rss_tool = RssTool(url="https://www.sportscollectorsdaily.com/category/sports-card-news/feed/",
					cache_duration=60*60*1,
					cache_directory=collectbot.filepath_cache_directory,
					cache_file="rss_sports-collector-daily.json")
	
	html_section = CollectBotTemplate.generate_html_section(
		title="Sports Cards News",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	rss_tool = RssTool(url="https://comicbook.com/feed/rss/",
					cache_duration=60*60*1,
					cache_directory=collectbot.filepath_cache_directory,
					cache_file="rss_comicbook-com.json")
	
	html_section = CollectBotTemplate.generate_html_section(
		title="Comic News",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	rss_tool = RssTool(urls=["https://puck.news/category/art/feed/",
						  "https://www.antiquesandthearts.com/feed/"],
							 cache_duration=60*30*3,
							 cache_directory=collectbot.filepath_cache_directory,
							 cache_file="rss_art-and-antiques.json")
	html_section: str = CollectBotTemplate.generate_html_section(
		title="Art & Antiques",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	#The feed at `https://blog.ha.com/feed/` is disallowed by `robots.txt`, SMH.
	# rss_tool = RssTool(urls=["https://blog.ha.com/feed/"],
	# 						 cache_duration=60*30*3,
	# 						 cache_directory=collectbot.filepath_cache_directory,
	# 						 cache_file="rss_high-end-auctions.json")
	# html_section: str = CollectBotTemplate.generate_html_section(
	# 	title="High End Auctions",
	# 	extensions=extensions,
	# 	fetch_func=rss_tool.fetch
	# )
	# buffer_html_auctions.write(html_section)

	rss_tool = RssTool(url="https://coinweek.com/feed/",
					cache_duration=60*60*4,
					cache_directory=collectbot.filepath_cache_directory,
					cache_file="rss_coin-week.json")
	
	html_section = CollectBotTemplate.generate_html_section(
		title="Coin News",
		extensions=extensions,
		fetch_func=rss_tool.fetch
	)
	buffer_html_auctions.write(html_section)

	buffer_html_auctions.write("</div>\n")
	buffer_html_auctions.write("</div>\n")

	buffer_html.write(CollectBotTemplate.make_news(buffer_html_auctions.getvalue()))

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		buffer_html.write(file.read())

	#Write to file named index.html
	filepath_output: str = path.join(collectbot.filepath_output_directory, collectbot.filename_output)
	with open(filepath_output, 'w', encoding="utf-8") as file:
		file.write(buffer_html.getvalue())
		logger.info(f"File {filepath_output} created.")


	#Backup the file
	FilePathTools.create_directory_if_not_exists("backup")
	FilePathTools.backup_file(filepath_output, "backup")

	logger.info(f"File {collectbot.filename_output} moved to backup.")
