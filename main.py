
import os
from typing import Callable
import json
import time
import hashlib
import uuid
import markdown
from io import StringIO
from dotenv import load_dotenv

# import requests
# import yaml


from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.tables import TableExtension

appid: uuid = uuid.UUID("27DC793C-9C69-4565-B611-9318933CA561")

load_dotenv()

# eBay API credentials (these should be stored securely, not hardcoded in the code)
EBAY_APPID = os.getenv('EBAY_APPID')
EBAY_CERTID = os.getenv('EBAY_DEVID')
EBAY_DEVID = os.getenv('EBAY_CERTID')

if not EBAY_APPID or not EBAY_CERTID or not EBAY_DEVID:
	msg: str = "Please set the EBAY_APPID, EBAY_CERTID, and EBAY_DEVID " \
				"environment variables."
	raise ValueError(msg)

class APICache:
	def __init__(self, cache_dir: str = "cache", cache_file: str = "api_cache.json", cache_ttl: int = 8 * 60 * 60):
		self.cache_dir = cache_dir
		self.cache_file = cache_file
		self.cache_ttl = cache_ttl
		if not os.path.exists(self.cache_dir):
			os.makedirs(self.cache_dir)
	
	def cache_file_path(self) -> str:
		return os.path.join(self.cache_dir, self.cache_file)

	def load_cache(self) -> list[dict[str, any]]:
		"""Load the cache from the file if it exists and is not expired."""
		cache_file_path: str = self.cache_file_path()
		if os.path.exists(cache_file_path):
			with open(cache_file_path, 'r') as f:
				cache_data: list[str, dict] = json.load(f)
				if time.time() - cache_data['timestamp'] < self.cache_ttl:
					return cache_data['data']
		return []

	def save_cache(self, data: list[dict[str, any]]):
		"""Save the data to the cache file with the current timestamp."""
		cache_data: dict[str, any] = {
			'data': data,
			'timestamp': time.time()
		}
		with open(self.cache_file_path(), 'w') as f:
			json.dump(cache_data, f, indent=4)

	def cached_api_call(self, func: Callable[[], list[dict[str, any]]], *args) -> list[dict[str, any]]:
		"""Fetches data from the cache or calls the API function and caches the result."""
		cached_data: list[dict[str, any]] = self.load_cache()
		if cached_data:
			return cached_data

		api_data: list[dict[str, any]] = func(*args)
		self.save_cache(api_data)
		return api_data

def search_top_watched_items(category_id: str, max_results: int=10) -> list[dict]:
	try:
		api: Finding = Finding(appid=EBAY_APPID, config_file=None, domain="svcs.ebay.com")
	
		request_params: dict[str, any] = {
			'categoryId': category_id,
			'outputSelector': 'WatchCount',
			'paginationInput': {
				'entriesPerPage': max_results
			},
			'sortOrder': 'WatchCountDecreaseSort',
			'itemFilter': [
				{'name': 'ListingType', 'value': 'Auction'}
			]
		}
		
		response = api.execute('findItemsAdvanced', request_params)
		items = response.dict().get('searchResult', {}).get('item', [])
		return items

	except ConnectionError as e:
		print(f"Error: {e}")
		print(e.response.dict())
		return []

def search_results_to_markdown(items: list[dict]) -> str:
	buffer = StringIO()
	if items:
		item: dict = None

		ctr: int = 0
		for item in items:
			title = item['title']
			watch_count = item['listingInfo']['watchCount']
			price = item['sellingStatus']['currentPrice']['value']
			currency = item['sellingStatus']['currentPrice']['_currencyId']
			item_url = item['viewItemURL']
			#image_url = item['galleryURL']
			#location = item['location']
			#condition = ""
			#try:
			#	condition = item['condition']['conditionDisplayName']
			#except:
			#	condition = "N/A"

			buffer.write(" * [")
			buffer.write(title)
			buffer.write("](")
			buffer.write(item_url)
			buffer.write(")\n")
			#listing_type = item['listingInfo']['listingType']
			#start_time = item['listingInfo']['startTime']
			#end_time = item['listingInfo']['endTime']

			ctr += 1

	else:
		print("No items found or an error occurred.")

	return buffer.getvalue()

def get_temp_dir() -> str:
	temp_dir: str = os.getenv('TMPDIR') or os.getenv('TEMP') or os.getenv('TMP') or '/tmp'
	if not os.path.exists(temp_dir):
		temp_dir = '/tmp'
	if not os.path.exists(temp_dir):
		raise ValueError("Cannot determine the temporary directory.")
	return temp_dir

def get_stable_temp_file_path(prefix: str, unique_id: str, extension: str) -> str:
	temp_dir: str = get_temp_dir()

	if not unique_id:
		raise ValueError("unique_id is required.")
	
	if not extension:
		raise ValueError("extension is required.")

	if not extension.startswith('.'):
		extension = '.' + extension

	unique_hash = hashlib.md5((prefix + unique_id).encode()).hexdigest()
	stable_filename = f"{prefix}_{unique_hash}{extension}"
	temp_file_path = os.path.join(temp_dir, stable_filename)

	return temp_file_path

def get_unique_temp_file_path(prefix: str, extension: str) -> str:
	temp_dir: str = get_temp_dir()

	if not extension.startswith('.'):
		extension = '.' + extension

	unique_filename = f"{prefix}_{os.getpid()}_{os.urandom(8).hex()}{extension}"
	temp_file_path = os.path.join(temp_dir, unique_filename)

	return temp_file_path

def search_top_items_from_catagory(category_id: str, category_name: str, ttl: int, buffer_md: StringIO) -> None:
	file_name: str = str.join(".", [str.zfill(category_id, 6), "json"])
	api_cache: APICache = APICache("cache", file_name, ttl)
	search_results: list[dict[str, any]] = api_cache.cached_api_call(search_top_watched_items, category_id)
	if search_results:
		buffer_md.write(f"## {category_name}\n")
		buffer_md.write(search_results_to_markdown(search_results))
	else:
		print(f"No items found in the {category_name} category.")
	search_results.clear()

'''
	Main function
'''
if __name__ == "__main__":

	buffer_md: StringIO = StringIO()
	buffer_md.write("# Auctions {: .header_1 }\n\n")
	refresh_time: int = 8 * 60 * 60

	search_top_items_from_catagory("212", "Trading Cards", refresh_time, buffer_md)
	search_top_items_from_catagory("259104", "Comics", refresh_time, buffer_md)
	search_top_items_from_catagory("11116", "Coins", refresh_time, buffer_md)
	search_top_items_from_catagory("253", "Coins 2", refresh_time, buffer_md)
	search_top_items_from_catagory("256", "Coins 3", refresh_time, buffer_md)
	search_top_items_from_catagory("260", "Stamps", refresh_time, buffer_md)

	buffer_html: StringIO = StringIO(initial_value="")
	with open('templates/header.html', 'r', encoding="utf-8") as input_file:
		buffer_html.write(input_file.read())

	string_html_body: str = markdown.markdown(buffer_md.getvalue(), extensions=[AttrListExtension(), TableExtension()])
	buffer_html.write(string_html_body)
	buffer_md.close()

	with open('templates/footer.html', 'r', encoding="utf-8") as file:
		buffer_html.write(file.read())

	#Write to file named index.html
	with open('index.html', 'w', encoding="utf-8") as file:
		file.write(buffer_html.getvalue())

	#Print the html
	#print(buffer_html.getvalue())
