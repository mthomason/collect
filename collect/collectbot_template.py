#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from io import StringIO
import logging
import markdown

from typing import Generator, Callable
from collect.ebayapi import EBayAuctions
from collect.html_template_processor import HtmlTemplateProcessor
from collect.string_adorner import StringAdorner
from collect.ebayapi import AuctionListing, AuctionListingSimple

logger = logging.getLogger(__name__)

class CollectBotTemplate:
	_adorner = StringAdorner()

	def __init__(self):
		pass

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
	
	def html_wrapper_no_content(tag: str, attributes: dict = None) -> str:
		assert tag, "tag is required."
		if not attributes:
			return f'<{tag} />'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs} />'

	def html_wrapper(tag: str, content: str, attributes: dict = None) -> str:
		assert tag, "tag is required."
		assert content, "content is required."
		if not attributes:
			return f'<{tag}>{content}</{tag}>'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs}>{content}</{tag}>'

	def generate_html_section(title: str, fetch_func: Callable[[], Generator[dict[str, str], None, None]]) -> str:
		buffer_html: StringIO = StringIO()
		buffer_html.write(CollectBotTemplate.make_item_header(title))

		buffer_li: StringIO = StringIO()
		for item in fetch_func():
			attribs: dict = {
				"href": item['link'],
				"target": "_blank"
			}
			link: str = CollectBotTemplate.html_wrapper(tag="a", content=item['title'], attributes=attribs)
			list_item: str = CollectBotTemplate.html_wrapper(tag="li", content=link)
			buffer_li.write(list_item)
			buffer_li.write("\n")

		buffer_html.write(CollectBotTemplate.make_content_ul(buffer_li.getvalue()))
		result: str = CollectBotTemplate.make_section(buffer_html.getvalue())
		buffer_li.seek(0)
		buffer_li.truncate(0)
		buffer_li.close()
		buffer_html.seek(0)
		buffer_html.truncate(0)
		buffer_html.close()
		return result

	def auctions_to_html(ebay: EBayAuctions, exclude: list[str]) -> str:
		bufauct: StringIO = StringIO()
		bufauct.write(CollectBotTemplate.make_section_header("Auctions"))

		bufsecs: StringIO = StringIO()
		for auction in ebay.auctions:

			bufsec: StringIO = StringIO()
			bufsec.write(CollectBotTemplate.make_item_header(auction['title']))
			auction_listings: list[AuctionListingSimple] = ebay._search_results_to_html(
				items=auction['items'],
				epn_category=auction['epn-category'],
				exclude=exclude)

			html_: str = ""
			for listing in auction_listings:
				attribs: dict = { "href": listing.url, "target": "_blank" }
				if listing.ending_soon:
					attribs["class"] = "a_ending"
				title: str = CollectBotTemplate.strip_outter_tag(markdown.markdown(listing.title))
				link: str = CollectBotTemplate.html_wrapper(tag="a", content=title, attributes=attribs)
				link = CollectBotTemplate.html_wrapper(tag="li", content=link)
				html_ += link + "\n"

			bufsec.write(CollectBotTemplate.make_content_ul(html_))
			bufsecs.write(CollectBotTemplate.make_section(bufsec.getvalue()))
			bufsec.close()
			
		bufauct.write(CollectBotTemplate.make_container(bufsecs.getvalue()))
		result: str = CollectBotTemplate.make_auctions(bufauct.getvalue())

		bufsecs.close()
		bufauct.close()
		return result

	def create_html_header() -> str:
		processor: HtmlTemplateProcessor = HtmlTemplateProcessor("templates/header.html")
		processor.replace_from_file("style_inline", "templates/style_inline.css")
		processor.replace_from_file("header_js", "templates/header_js.html")
		return processor.get_content()
	
	def create_html_footer() -> str:
		with open('templates/footer.html', 'r', encoding="utf-8") as file:
			return file.read()
		
	def strip_outter_tag(s: str) -> str:
		""" strips outer html tags """
		start = s.find('>')+1
		end = len(s)-s[::-1].find('<')-1
		return s[start:end]

	@_adorner.md_adornment("**")
	def md_make_bold(s: str) -> str: return s

	@_adorner.md_adornment("*")
	def md_make_italic(s: str) -> str: return s
	
	@_adorner.html_wrapper_attributes("div", {"id": "newspaper"})
	def make_newspaper(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"id": "nameplate"})
	@_adorner.html_wrapper_attributes("h1", {"class": "h1"})
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
	@_adorner.html_wrapper_attributes("ul", {})
	def make_content_ul(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "content"})
	def make_content(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "section-header"})
	@_adorner.html_wrapper_attributes("h2", {"class": "h2"})
	def make_section_header(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "item-header"})
	@_adorner.html_wrapper_attributes("h3", {"class": "h3"})
	def make_item_header(s: str) -> str: return s
