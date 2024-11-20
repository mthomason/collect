# README: Hobby Report

This script creates a Drudge Report type site for collectors using eBay listings, RSS feeds, and OpenAI's Function Calling API.

The purpose of this app is to demonstrate OpenAI's function calling API.  Here it's used to programmatically cleanup and standardize auction headlines.  A simular use would be to have it pull top players names from the most popular eBay trading card auctions, and make a list of top players.

Below is my `.env` file.

You just pip install the `requirements.txt`, probably in a virtual python 3.12+ environment.  Then you run the `collect` app.

```bash
################################################################################
#AWS Keys
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

#CloudFront Keys
AWS_CF_DISTRIBUTION_ID = ''

################################################################################
#eBay API Keys
EBAY_APPID = ''
EBAY_DEVID = ''
EBAY_CERTID = ''

################################################################################
#eBay Partner Network Keys
EPN_TRACKING_ID = ''

################################################################################
#OpenAI API Keys
OPENAI_API_KEY = ''

################################################################################
#Reddit API Keys
REDDIT_CLIENT_ID = ''
REDDIT_CLIENT_SECRET = ''
REDDIT_USER_AGENT = ''
```
