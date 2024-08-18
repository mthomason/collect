# /collect/ebayapi.py
# -*- coding: utf-8 -*-

import os
import re
import urllib.parse
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, ParseResult

class eBayAPIHelper:
	def __init__(self):
		self.appid = os.getenv('EBAY_APPID')
		self.certid = os.getenv('EBAY_CERTID')
		self.devid = os.getenv('EBAY_DEVID')

		if not self.appid or not self.certid or not self.devid:
			raise ValueError("Please set the EBAY_APPID, EBAY_CERTID, and EBAY_DEVID environment variables.")

		# Initialize the eBay API connection
		self.api = Finding(appid=self.appid, config_file=None, domain="svcs.ebay.com")

	@staticmethod
	def generate_epn_link(original_url: str, campaign_id: str, custom_id: str = "") -> str:
		base_params: dict[str, str] = {
			'mkcid': '1',
			'mkrid': '711-53200-19255-0',
			'siteid': '0',
			'campid': campaign_id,
			'customid': custom_id,
			'toolid': '10001',
			'mkevt': '1'
		}

		url_parts: ParseResult = urlparse(original_url)
		url_path_new: str = url_parts.path
		match = re.search(r'/itm/[\w-]+/(\d+)', url_path_new)
		if match:
			url_path_new = f'/itm/{match.group(1)}'

		query: dict = dict(parse_qsl(url_parts.query))
		query.update(base_params)
		url_new: ParseResult = ParseResult(url_parts.scheme, url_parts.netloc, url_path_new, url_parts.params, urlencode(query), url_parts.fragment)
		return urlunparse(url_new)

	@staticmethod
	def generate_epn_link_rover(ebay_url: str, tracking_id: str, campaign_id: str) -> str:
		program_id = "710-53481-19255-0"  # Check your EPN account for the correct value
		encoded_url = urllib.parse.quote(ebay_url)
		partner_link = f"https://rover.ebay.com/rover/1/{program_id}/{tracking_id}/{campaign_id}?mpre={encoded_url}"
		return partner_link

	def search_top_watched_items(self, category_id: str, max_results: int = 10) -> list[dict[str, any]]:
		try:
			request_params = {
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

			response = self.api.execute('findItemsAdvanced', request_params)
			items = response.dict().get('searchResult', {}).get('item', [])
			return items

		except ConnectionError as e:
			print(f"Error: {e}")
			print(e.response.dict())
			return []

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
