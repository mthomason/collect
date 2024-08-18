#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import urllib.parse
import json
import markdown

from collect.apicache import APICache
from collect.aws_helper import AwsS3Helper
from collect.imagecache import ImageCache
from collect.promptchat import PromptPersonalityAuctioneer
from datetime import datetime, timedelta
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from io import StringIO
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, ParseResult


class AuctionListing(NamedTuple):
	image: str
	title: str
	url: str
	ending_soon: bool


class eBayAPIHelper:
	def __init__(self):
		self.appid = os.getenv('EBAY_APPID')
		self.certid = os.getenv('EBAY_CERTID')
		self.devid = os.getenv('EBAY_DEVID')

		if not self.appid or not self.certid or not self.devid:
			raise ValueError("Please set the EBAY_APPID, EBAY_CERTID, and EBAY_DEVID environment variables.")

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

class EBayAuctions:
	def __init__(self, filepath_cache_directory: str = "cache",
				 filepath_image_directory: str = "httpd/i",
				 refresh_time=8 * 60 * 60):
		self._ebay_api: eBayAPIHelper = eBayAPIHelper()
		self._api_cache: APICache = APICache(filepath_cache_directory)
		self._image_dir: str = filepath_image_directory
		self._refresh_time: int = refresh_time

		with open("config/auctions-ebay.json", "r") as file:
			self._auctions: list[dict[str, any]] = json.load(file)

	@property
	def auctions(self) -> list[dict[str, any]]:
		return self._auctions

	def load_auctions(self):
		for auction in self._auctions:
			auction['items'] = self._search_top_items_from_catagory(
				auction['id'],
				ttl=self._refresh_time,
				max_results=auction['count']
			)
		return self._auctions
	
	def most_watched(self) -> dict[str, any]:
		return max(
			[item for cat in self._auctions for item in cat['items']],
			key=lambda x: int(x['listingInfo']['watchCount'])
		)
	
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

	def top_item_to_markdown(self, item: dict[str, any], epn_category: str) -> AuctionListing:
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

		auction_listing: AuctionListing = AuctionListing(
			image=str(Path('i') / path_obj.name),
			title=title,
			url=epn_url,
			ending_soon=end_datetime - now < timedelta(days=1)
		)
		return auction_listing

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

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
