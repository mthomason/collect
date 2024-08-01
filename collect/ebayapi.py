import os
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError

class eBayAPI:
	def __init__(self):
		# eBay API credentials (these should be stored securely, not hardcoded in the code)
		self.appid = os.getenv('EBAY_APPID')
		self.certid = os.getenv('EBAY_CERTID')
		self.devid = os.getenv('EBAY_DEVID')

		if not self.appid or not self.certid or not self.devid:
			raise ValueError("Please set the EBAY_APPID, EBAY_CERTID, and EBAY_DEVID environment variables.")

		# Initialize the eBay API connection
		self.api = Finding(appid=self.appid, config_file=None, domain="svcs.ebay.com")

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
