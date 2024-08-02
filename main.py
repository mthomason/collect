# /main.py
# -*- coding: utf-8 -*-

from dotenv import load_dotenv

import uuid
import markdown
from io import StringIO

from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.tables import TableExtension
from datetime import datetime, timedelta

from collect.apicache import APICache
from collect.imagecache import ImageCache
from collect.ebayapi import eBayAPI
from collect.promptchat import PromptPersonalityAuctioneer

if not load_dotenv():
	raise ValueError("Failed to load the .env file.")

app_id: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")
app_name: str = "Hobby Report"

def top_item_to_markdown(item_id: str, items: list[dict[str, any]]) -> str:
	"""This is the most watched collectable item."""
	item: dict[str, any] = None
	for item in items:
		if item['itemId'] == item_id:
			break

	if not item:
		raise ValueError("Item not found in the list.")

	buffer: StringIO = StringIO()
	title: str = item['title']
	watch_count: int = item['listingInfo']['watchCount']
	price: float = item['sellingStatus']['currentPrice']['value']
	currency: str = item['sellingStatus']['currentPrice']['_currencyId']
	item_url: str = item['viewItemURL']
	top_rated_listing: bool = bool(str.lower(item['topRatedListing']) in ['true', '1'])
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
	# buffer.write(image_url)
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

		auctioneer = PromptPersonalityAuctioneer()

		buffer_additional_prompt: StringIO = StringIO()
		buffer_additional_prompt.write("\n```xml\n")
		buffer_additional_prompt.write("{\n")
		buffer_additional_prompt.write("<headlines>\n")

		# Generate additional prompt for the auctioneer
		for item in items:
			item_id = item['itemId']
			if exclude and item_id in exclude:
				continue

			title = item['title']
			buffer_additional_prompt.write("  <headline>\n")
			buffer_additional_prompt.write("    <title>")
			buffer_additional_prompt.write(title)
			buffer_additional_prompt.write("</title>\n")
			buffer_additional_prompt.write("    <item_id>")
			buffer_additional_prompt.write(item_id)
			buffer_additional_prompt.write("</item_id>\n")
			buffer_additional_prompt.write("    </headline>\n")

		buffer_additional_prompt.write("</headlines>\n``\n\n`")

		headlines_ids: dict[str, str] = {}

		headlines_iterator = auctioneer.get_headlines(buffer_additional_prompt.getvalue())
		for headline in headlines_iterator:
			headlines_ids[headline['identifier']] = headline['headline']

		for item in items:
			item_id = item['itemId']
			if exclude and item_id in exclude:
				continue
			
			title = headlines_ids.get(item_id)
			#title = item['title']
			watch_count = item['listingInfo']['watchCount']
			price = item['sellingStatus']['currentPrice']['value']
			currency = item['sellingStatus']['currentPrice']['_currencyId']
			item_url = item['viewItemURL']

			top_rated_listing: bool = bool(str.lower(item['topRatedListing']) in ['true', '1'])
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


		#if ctr > 0:
		#	buffer.write("</td></tr></table>\n")
		#else:
		#	print("No items found or an error occurred.")

	#buffer.write("</td></tr></table>\n\n")
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

	with open('templates/header.html', 'r', encoding="utf-8") as input_file:
		buffer_html.write(input_file.read())


	buffer_md.write("# Hobby Report {: .header_1 }\n\n")
	buffer_md.write(top_item_md)

	buffer_md.write("## Auctions {: .header_2 }\n\n")


	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)

	buffer_html.write("<div class=\"section\">\n")
	buffer_md.write("\n")
	buffer_md.write("### Trading Cards {: .header_3 }\n\n")
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)
	buffer_html.write("<div class=\"content\">\n")
	write_top_items_md_to_buffer("Trading Cards", items_trading_cards, buffer_md, exclude=[top_item_id])
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_html.write("</div>\n")
	buffer_html.write("</div>\n")
	buffer_md.seek(0)
	buffer_md.truncate(0)


	buffer_html.write("<div class=\"section\">")
	buffer_md.write("\n")
	buffer_md.write("### Non Sports {: .header_3 }\n\n")
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)
	buffer_html.write("<div class=\"content\">\n")
	write_top_items_md_to_buffer("Non Sports", items_non_sports, buffer_md, exclude=[top_item_id])
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_html.write("</div>\n")
	buffer_html.write("</div>\n")
	buffer_md.seek(0)
	buffer_md.truncate(0)


	buffer_html.write("<div class=\"section\">\n")
	buffer_md.write("\n### Comics {: .header_3 }\n\n")
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)
	buffer_html.write("<div class=\"content\">\n")
	write_top_items_md_to_buffer("Comics", items_comics, buffer_md, exclude=[top_item_id])
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_html.write("</div>\n")
	buffer_html.write("</div>\n")
	buffer_md.seek(0)
	buffer_md.truncate(0)


	buffer_html.write("<div class=\"section\">\n")
	buffer_md.write("\n### Coins {: .header_3 }\n\n")
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)
	buffer_html.write("<div class=\"content\">\n")
	write_top_items_md_to_buffer("Coins", items_coins, buffer_md, exclude=[top_item_id])
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_html.write("</div>\n")
	buffer_html.write("</div>\n")
	buffer_md.seek(0)
	buffer_md.truncate(0)

	buffer_html.write("<div class=\"section\">\n")
	buffer_md.write("\n### Stamps {: .header_3 }\n\n")
	buffer_html.write(markdown.markdown(buffer_md.getvalue(), extensions=extensions))
	buffer_md.seek(0)
	buffer_md.truncate(0)
	buffer_html.write("<div class=\"content\">\n")
	write_top_items_md_to_buffer("Stamps", items_stamps, buffer_md, exclude=[top_item_id])
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

	#string_html_body: str = markdown.markdown(buffer_md.getvalue(), extensions=extensions)
	#buffer_html.write(string_html_body)
	buffer_md.close()

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		buffer_html.write(file.read())

	#Write to file named index.html
	with open('index.html', 'w', encoding="utf-8") as file:
		file.write(buffer_html.getvalue())

	#Print the html
	#print(buffer_html.getvalue())
