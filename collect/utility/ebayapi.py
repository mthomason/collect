#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import urllib.parse
import json
import logging

from .apicache import APICache
from .aws_helper import AwsS3Helper
from .core.imagecache import ImageCache
from .promptchat import PromptPersonalityAuctioneer
from datetime import datetime, timedelta
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from os import path
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl, ParseResult

logger = logging.getLogger(__name__)

class AuctionListingSimple(NamedTuple):
	identifier: str
	title: str
	url: str
	ending_soon: bool
	end_datetime: datetime

class AuctionListing(NamedTuple):
	identifier: str
	title: str
	url: str
	ending_soon: bool
	image: str
	end_datetime: datetime

class eBayAPIHelper:
	def __init__(self):
		self.appid = os.getenv("EBAY_APPID")
		self.certid = os.getenv("EBAY_CERTID")
		self.devid = os.getenv("EBAY_DEVID")

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
			logger.error(f"Error: {e}")
			return []

class EBayAuctions:
	def __init__(self, filepath_cache_directory: str = "cache/",
				 filepath_image_directory: str = "httpd/i",
				 filepath_config_directory: str = "config/",
				 refresh_time: int=8 * 60 * 60,
				 user_agent: str | None = None):
		self._ebay_api: eBayAPIHelper = eBayAPIHelper()
		self._api_cache: APICache = APICache(filepath_cache_directory)
		self._image_dir: str = filepath_image_directory
		self._refresh_time: int = refresh_time
		self._cache_dir = filepath_cache_directory
		self._user_agent: str | None = user_agent

		auctions_list: str = path.join(filepath_config_directory, "auctions-ebay.json")
		with open(auctions_list, "r") as file:
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
	
	def max_price(self) -> dict[str, any]:
		return max(
			[item for cat in self._auctions for item in cat['items']],
			key=lambda x: float(x['sellingStatus']['currentPrice']['value'])
		)
	
	def top_n_most_watched(self, n: int, exclude: list[str] = []) -> list[dict[str, any]]:
		items = [
			item for cat in self._auctions for item in cat['items']
			if item['itemId'] not in exclude
		]
		top_items = sorted(items, key=lambda x: int(x['listingInfo']['watchCount']), reverse=True)[:n]
		return top_items
	

	def top_n_sorted_auctions_static(items: list, n: int) -> list[dict[str, any]]:
		max_watchers = max(
			int(item['listingInfo']['watchCount']) for item in items
		)
		max_price = max(
			float(item['sellingStatus']['currentPrice']['value']) for item in items
		)

		# Define the sort factor calculation
		def calculate_sort_factor(item):
			watchers = int(item['listingInfo']['watchCount'])
			price = float(item['sellingStatus']['currentPrice']['value'])
			normalized_watchers = watchers / max_watchers if max_watchers else 0
			normalized_price = price / max_price if max_price else 0
			weight_watchers = 0.7
			weight_price = 0.3
			return (weight_watchers * normalized_watchers) + (weight_price * normalized_price)

		# Sort items by the calculated sort factor
		sorted_items = sorted(items, key=calculate_sort_factor, reverse=True)[:n]

		return sorted_items

	def top_n_sorted_auctions(self, n: int, exclude: list[str] = []) -> list[dict[str, any]]:
		items = [
			item for cat in self._auctions for item in cat['items']
			if item['itemId'] not in exclude
		]

		return EBayAuctions.top_n_sorted_auctions_static(items, n)

	def _search_results_to_html(self, items: list[dict], epn_category: str,
							exclude:list[str] = None) -> list[AuctionListingSimple]:
		return self._search_results_to_markdown(items, epn_category, exclude)

	def _search_top_items_from_catagory(self, category_id: str, ttl: int, max_results: int) -> list[dict[str, any]]:
		if not category_id or len(category_id) > 6:
			raise ValueError("category_id is required and must be less than six characters.")

		self._api_cache.cache_file = str.join(".", [str.zfill(category_id, 6), "json"])	
		search_results: list[dict[str, any]] = self._api_cache.cached_api_call(
			self._ebay_api.search_top_watched_items,
			category_id, max_results
		)
		return EBayAuctions.top_n_sorted_auctions_static(search_results, max_results)

	def process_and_upload_image(self, item: dict) -> str:
		"""
		Process an image URL, download the image if necessary, upload it to S3, 
		and return the image path.

		:param self: The instance containing configurations like cache directories.
		:param item: The dictionary containing the item's details including the image URL and itemId.
		:param download_images: A boolean flag indicating whether images should be downloaded.
		:return: The relative path of the image uploaded to S3.
		"""
		image_url: str = item['galleryURL']
		image_url_large: str = ""
		path_obj: Path | None = None

		if image_url.endswith("s-l140.jpg"):
			image_url = image_url.replace("s-l140.jpg", "s-l400.jpg")
		if image_url.endswith("s-l400.jpg"):
			image_url_large = image_url.replace("s-l400.jpg", "s-l1600.jpg")

		# Attempt to cache the main image, fallback on error
		try:
			image_cache = ImageCache(
				url=image_url, identifier=item['itemId'],
				cache_dir=self._image_dir, user_agent=self._user_agent
			)
		except Exception as e:
			logger.error(f"Error: {e}")
			image_cache = ImageCache(
				url=item['galleryURL'],
				identifier=item['itemId'],
				cache_dir=self._image_dir,
				user_agent=self._user_agent
			)

		# Ensure images are downloaded
		image_cache.download_image_if_needed()
		if image_url_large:
			image_cache_large = ImageCache(
				url=image_url_large,
				identifier=item['itemId'] + "_large",
				cache_dir=self._image_dir,
				user_agent=self._user_agent
			)
			image_cache_large.download_image_if_needed()

		local_path = image_cache.image_path
		aws_helper = AwsS3Helper(
			bucket_name='hobbyreport.net',
			region='us-east-1',
			ensure_bucket=False,
			cache_dir=self._cache_dir
		)

		path_obj = Path(local_path)
		aws_helper.upload_file_if_changed(
			local_path,
			f"i/{path_obj.name}"
		)
		return str(Path('i') / path_obj.name)

	def top_item_to_markdown(self, item: dict[str, any], epn_category: str,
							 download_images: bool = True) -> AuctionListing:
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

		del auctioneer

		item_url: str = item['viewItemURL']
		epn_url: str = eBayAPIHelper.generate_epn_link(item_url, epn_category)
		end_time_string: str = item['listingInfo']['endTime']
		end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
		now: datetime = datetime.now(tz=end_datetime.tzinfo)
		image: str = ""

		if download_images:
			image = self.process_and_upload_image(item)

		auction_listing: AuctionListing = AuctionListing(
			identifier=item['itemId'],
			image=image,
			title=title,
			url=epn_url,
			ending_soon=end_datetime - now < timedelta(days=1),
			end_datetime=end_datetime
		)
		return auction_listing

	def _search_results_to_markdown(self, items: list[dict], epn_category: str,
								exclude:list[str] = None) -> list[AuctionListingSimple]:
		"""Converts a list of search results to markdown."""
		auction_listings: list[AuctionListingSimple] = []
		if not items or len(items) == 0:
			return auction_listings

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

		del auctioneer

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

			epn_url = eBayAPIHelper.generate_epn_link(item['viewItemURL'], epn_category)
			end_time_string: str = item['listingInfo']['endTime']
			end_datetime: datetime = datetime.strptime(end_time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
			now: datetime = datetime.now(tz=end_datetime.tzinfo)

			if end_datetime > now:
				auction_listing_simple: AuctionListingSimple = AuctionListingSimple(
					identifier=item_id,
					title=title,
					url=epn_url,
					ending_soon=end_datetime - now < timedelta(days=1),
					end_datetime=end_datetime
				)
				auction_listings.append(auction_listing_simple)
				ctr += 1

		return auction_listings

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
