#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from io import StringIO
from os import path
import logging
import markdown

from collect.listitem import ListItem, TimeItem, IntItem, UnorderedList
from collect.listitem import UnorderedList, DescriptionList, TimeItem, IntItem, StrItem, LinkItem, ListItemsCollection
from collect.ebayapi import EBayAuctions, AuctionListing, AuctionListingSimple
from core.html_template_processor import HtmlTemplateProcessor
from core.string_adorner import StringAdorner, HtmlWrapper
from typing import Generator, Callable, Final

logger = logging.getLogger(__name__)


class CollectBotTemplate:
	_adorner = StringAdorner()
	_html_feature_trailing_slash_on_void: Final[bool] = False

	def __init__(self):
		pass

	def create_sitemap(self, urls: list[str]) -> str:
		b: StringIO = StringIO()
		b.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
		b.write("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
		for url in urls:
			b.write("\t<url>\n")
			b.write(f"\t\t<loc>{url}</loc>\n")
			b.write("\t\t<lastmod>")
			b.write(datetime.now().astimezone(timezone.utc).isoformat(timespec='minutes'))
			b.write("</lastmod>\n")
			b.write("\t\t<changefreq>hourly</changefreq>\n")
			b.write("\t\t<priority>1.0</priority>\n")
			b.write("\t</url>\n")

		b.write("</urlset>\n")
		r: str = b.getvalue()
		b.close()
		return r
	
	def html_wrapper_no_content(tag: str, attributes: dict = {}) -> str:
		assert tag, "tag is required."
		if len(attributes) == 0:
			if CollectBotTemplate._html_feature_trailing_slash_on_void:
				return f'<{tag} />'
			else:
				return f'<{tag}>'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		result: str = ""
		if CollectBotTemplate._html_feature_trailing_slash_on_void:
			result = f'<{tag} {attrs} />'
		else:
			result = f'<{tag} {attrs}>'
		return result

	def html_wrapper(tag: str, content: str, attributes: dict = None) -> str:
		assert tag, "tag is required."
		assert content, "content is required."
		if not attributes:
			return f'<{tag}>{content}</{tag}>'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs}>{content}</{tag}>'

	def generate_html_section(
			title: str,
			fetch_func: Callable[[], Generator[dict[str, str], None, None]]
		) -> str:
		buffer_html: StringIO = StringIO()
		buffer_html.write(CollectBotTemplate.make_item_header(title))
		buffer_li: StringIO = StringIO()
		for item in fetch_func():
			link: str = CollectBotTemplate.html_wrapper(
				tag="a", content=item['title'],
				attributes={"href": item['link']}
			)
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
				attribs: dict = { "href": listing.url }
				if listing.ending_soon:
					attribs["class"] = "aending"
				title: str = CollectBotTemplate.strip_outter_tag(markdown.markdown(listing.title))
				link: str = CollectBotTemplate.html_wrapper(tag="a", content=title, attributes=attribs)
				link = CollectBotTemplate.html_wrapper(tag="li", content=link)
				html_ += link + "\n"

			bufsec.write("\n")
			content_ol: str = CollectBotTemplate.make_content_ol(html_)
			bufsec.write(content_ol)
			bufsec.write("\n")
			section: str = CollectBotTemplate.make_section(bufsec.getvalue())
			bufsecs.write(section)
			bufsecs.write("\n")
			bufsec.seek(0)
			bufsec.truncate(0)
			bufsec.close()

		bufauct.write(CollectBotTemplate.make_container(bufsecs.getvalue()))
		bufauct.write("\n")
		result: str = CollectBotTemplate.make_auctions(bufauct.getvalue())

		bufsecs.close()
		bufauct.close()
		return result + "\n"

	def create_html_header(template_folder: str) -> str:
		
		processor: HtmlTemplateProcessor = HtmlTemplateProcessor(
			template_path=path.join(template_folder, "header.html")
		)
		processor.replace_from_file(
			"style_inline",
			path.join(template_folder, "style_inline.css")
		)
		processor.replace_from_file(
			"header_js",
			path.join(template_folder, "header_js.html")
		)
		return processor.get_content()
	
	def create_html_end(template_folder: str) -> str:
		p: str = path.join(template_folder, "footer.html")
		with open(p, "r", encoding="utf-8") as file:
			return file.read()
		
	def strip_outter_tag(s: str) -> str:
		""" strips outer html tags """
		start = s.find('>')+1
		end = len(s)-s[::-1].find('<')-1
		return s[start:end]

	def make_featured_image(src: str, alt: str) -> str:
		s: str = HtmlWrapper.html_item(
			tag="img",
			attributes={
				"src": src,
				"class": "thi",
				"alt": alt
			}
		)
		return HtmlWrapper.wrap_html(content=s, tag="p")
	
	@_adorner.html_wrapper_attributes("main", {"id": "hrpt"})
	def make_newspaper(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("ol", {})
	def make_above_fold_links(links: list[AuctionListing]) -> str:
		buf: StringIO = StringIO()
		for link in links:
			attribs: dict = { "href": link.url }
			if link.ending_soon:
				attribs["class"] = "aending"
			title: str = CollectBotTemplate.strip_outter_tag(markdown.markdown(link.title))
			link: str = CollectBotTemplate.html_wrapper(tag="a", content=title, attributes=attribs)
			link = CollectBotTemplate.html_wrapper(tag="li", content=link)
			buf.write(link)
			buf.write("\n")

		html_: str = buf.getvalue()
		buf.close()
		return html_

	@_adorner.html_wrapper_attributes("aside", {"id": "above-fold"})
	def make_above_fold(s: str, links: list[AuctionListing]) -> str:
		buf: StringIO = StringIO()
		buf.write(CollectBotTemplate.make_section_header(s))
		buf.write("\n")
		buf.write(CollectBotTemplate.make_above_fold_links(links))
		html_: str = buf.getvalue()
		buf.close()
		return html_
	
	def make_lead_headline_body(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("section", {"id": "lead-headline"})
	def make_lead_headline(s: str, body: str) -> str:
		buf: StringIO = StringIO()
		buf.write(CollectBotTemplate.make_section_header(s))
		buf.write("\n")
		buf.write(CollectBotTemplate.make_lead_headline_body(body))
		html_: str = buf.getvalue()
		buf.close()
		return html_

	@_adorner.html_wrapper_attributes("article", {"id": "auctions"})
	def make_auctions(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("article", {"id": "news"})
	def make_news(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "container"})
	def make_container(s: str) -> str: return s

	@_adorner.html_wrapper("section")
	def make_section(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("ul", {})
	def make_content_ul(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("ol", {})
	def make_content_ol(s: str) -> str: return s

	@_adorner.html_wrapper("footer")
	def make_footer(title: str, items: ListItemsCollection) -> str:
		header: str = CollectBotTemplate.make_section_header(title)
		body: str = items.gethtml()
		return header + body

	@_adorner.html_wrapper("header")
	@_adorner.html_wrapper("h1")
	def make_nameplate(s: str) -> str: return s

	@_adorner.html_wrapper("h2")
	def make_section_header(s: str) -> str: return s

	@_adorner.html_wrapper("h3")
	def make_item_header(s: str) -> str: return s

if __name__ == '__main__':
	raise ValueError("This script is not meant to be run directly.")
