# /main.py
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

import uuid
import markdown
import json
from io import StringIO

from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.tables import TableExtension
from datetime import datetime, timedelta

from collect.filepathtools import FilePathTools
from collect.apicache import APICache
from collect.imagecache import ImageCache
from collect.ebayapi import eBayAPI
from collect.promptchat import PromptPersonalityAuctioneer

def top_item_to_markdown(item_id: str, items: list[dict[str, any]]) -> str:
	"""This is the most watched collectable item."""
	item: dict[str, any] = None
	for item in items:
		if item['itemId'] == item_id:
			break

	if not item:
		raise ValueError("Item not found in the list.")

	auctioneer: PromptPersonalityAuctioneer = PromptPersonalityAuctioneer()
	auctioneer.add_headline(item['title'], item_id)
	
	headlines_iterator = auctioneer.get_headlines()
	title: str = ""
	for headline in headlines_iterator:
		title = headline['headline']
		break

	buffer: StringIO = StringIO()
	#title: str = item['title']
	#watch_count: int = item['listingInfo']['watchCount']
	#price: float = item['sellingStatus']['currentPrice']['value']
	#currency: str = item['sellingStatus']['currentPrice']['_currencyId']
	#top_rated_listing: bool = bool(str.lower(item['topRatedListing']) in ['true', '1'])
	item_url: str = item['viewItemURL']
	end_time_string: str = item['listingInfo']['endTime']
	end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
	now: datetime = datetime.now(tz=end_datetime.tzinfo)

	image_url = item['galleryURL']
	
	if image_url.endswith("s-l140.jpg"):
		image_url = image_url.replace("s-l140.jpg", "s-l400.jpg")
	
	try:
		image_cache = ImageCache(url=image_url, identifier=item_id)
	except Exception as e:
		image_cache = ImageCache(url=item['galleryURL'], identifier=item_id)
		print(f"Error: {e}")

	local_path = image_cache.get_image_path()

	buffer.write("![image](")
	buffer.write(local_path)
	buffer.write("){: .top_headline_image }\n\n")

	buffer.write("**[")
	buffer.write(title)
	buffer.write("](")
	buffer.write(item_url)
	buffer.write("){: .top_headline }**\n\n")

	return buffer.getvalue()

def search_results_to_markdown(items: list[dict], exclude:list[str] = None) -> str:
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

			auctioneer.add_headline(item['title'], item_id)

		headlines_ids: dict[str, str] = {}
		headlines_iterator = auctioneer.get_headlines()

		for headline in headlines_iterator:
			headlines_ids[headline['identifier']] = headline['headline']

		auctioneer.clear_headlines()

		for item in items:
			item_id = item['itemId']
			if exclude and item_id in exclude:
				continue
			
			title = headlines_ids.get(item_id)
			if not title:
				title = item['title']
			#watch_count = item['listingInfo']['watchCount']
			#price = item['sellingStatus']['currentPrice']['value']
			#currency = item['sellingStatus']['currentPrice']['_currencyId']
			#top_rated_listing: bool = bool(str.lower(item['topRatedListing']) in ['true', '1'])

			item_url = item['viewItemURL']
			end_time_string: str = item['listingInfo']['endTime']
			end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
			now: datetime = datetime.now(tz=end_datetime.tzinfo)

			if end_datetime > now:

				if ctr == 0:
					image_url = item['galleryURL']
					buffer.write("![image](")
					buffer.write(image_url)
					buffer.write(")\n\n")

				buffer.write(" * [")
				buffer.write(title)
				buffer.write("](")
				buffer.write(item_url)

				if end_datetime - now < timedelta(days=1):
					buffer.write("){: .ending_soon}\n")
				else:
					buffer.write(")\n")

				ctr += 1

	return buffer.getvalue()

def search_top_items_from_catagory(category_id: str, ttl: int) -> list[dict[str, any]]:
	file_name: str = str.join(".", [str.zfill(category_id, 6), "json"])
	api_cache: APICache = APICache("cache", file_name, ttl)
	ebay_api: eBayAPI = eBayAPI()

	search_results: list[dict[str, any]] = api_cache.cached_api_call(ebay_api.search_top_watched_items, category_id)
	return search_results

def write_top_items_md_to_buffer(category_name: str, search_results: list[dict[str, any]], buffer_md: StringIO, exclude: list[str] = None) -> None:
	if not search_results:
		raise ValueError("search_results is required.")
	
	buffer_md.write(search_results_to_markdown(search_results, exclude))

	return None

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
	
'''
	Main function
'''
if __name__ == "__main__":

	# Program Initalization
	if not load_dotenv():
		raise ValueError("Failed to load the .env file.")

	# Set Inital Values
	app_id: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")
	app_name: str = "Hobby Report"

	buffer_md: StringIO = StringIO()
	refresh_time: int = 8 * 60 * 60
	top_item_id: str = ""

	buffer_html: StringIO = StringIO(initial_value="")
	extensions: list[str] = ['attr_list']

	items_trading_cards: list[dict[str, any]] = search_top_items_from_catagory("212", ttl=refresh_time)
	items_non_sports: list[dict[str, any]] = search_top_items_from_catagory("183050", ttl=refresh_time)
	items_comics: list[dict[str, any]] = search_top_items_from_catagory("259104", ttl=refresh_time)
	items_coins: list[dict[str, any]] = search_top_items_from_catagory("253", ttl=refresh_time)	
	items_stamps: list[dict[str, any]] = search_top_items_from_catagory("260", ttl=refresh_time)

	all_items: list[dict[str, any]] = items_trading_cards.copy()
	all_items.extend(items_non_sports)
	all_items.extend(items_comics)
	all_items.extend(items_coins)
	all_items.extend(items_stamps)

	top_item_id = get_top_item_id(all_items)

	top_item_md = top_item_to_markdown(top_item_id, all_items)

	all_items.clear()

	# Write the HTML header
	with open('templates/header.html', 'r', encoding="utf-8") as input_file:
		buffer_html.write(input_file.read())

	# Write the markdown header
	buffer_md.write("# Hobby Report {: .header_1 }\n\n")
	buffer_md.write(top_item_md)

	buffer_md.write("## Auctions {: .header_2 }\n\n")

	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)

	sections: list[dict[str, object]] = [
			{"header": "Trading Cards", "items": items_trading_cards, "exclude": [top_item_id]},
			{"header": "Non Sports", "items": items_non_sports, "exclude": [top_item_id]},
			{"header": "Comics", "items": items_comics, "exclude": [top_item_id]},
			{"header": "Coins", "items": items_coins, "exclude": [top_item_id]},
			{"header": "Stamps", "items": items_stamps, "exclude": [top_item_id]},
		]

	for section in sections:
		buffer_html.write("<div class=\"section\">\n")
		buffer_md.write("\n### ")
		buffer_md.write(section['header'])
		buffer_md.write(" {: .header_3 }\n\n")
		buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
		buffer_md.seek(0)
		buffer_md.truncate(0)
		buffer_html.write("<div class=\"content\">\n")
		write_top_items_md_to_buffer(section['header'], section['items'], buffer_md, exclude=section['exclude'])
		buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
		buffer_html.write("</div>\n")
		buffer_html.write("</div>\n")
		buffer_md.seek(0)
		buffer_md.truncate(0)

	items_trading_cards.clear()
	items_non_sports.clear()
	items_comics.clear()
	items_coins.clear()
	items_stamps.clear()

	buffer_md.close()

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		buffer_html.write(file.read())

	#Write to file named index.html
	with open('index.html', 'w', encoding="utf-8") as file:
		file.write(buffer_html.getvalue())

	#Backup the file
	FilePathTools.create_directory_if_not_exists("backup")
	FilePathTools.backup_file("index.html", "backup")
