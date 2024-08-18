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
	
	def html_wrapper(tag: str, content: str, attributes: dict = None) -> str:
		assert tag, "tag is required."
		assert content, "content is required."
		if not attributes:
			return f'<{tag}>{content}</{tag}>'
		attrs = " ".join([f'{k}="{v}"' for k, v in (attributes or {}).items()])
		return f'<{tag} {attrs}>{content}</{tag}>'

	def generate_html_section(title: str, fetch_func: Callable[[], Generator[dict[str, str], None, None]]) -> str:
		buffer_html: StringIO = StringIO()
		buffer_html.write("<div class=\"section\">\n")
		buffer_html.write(CollectBotTemplate.make_h3(title))
		buffer_html.write("\n<div class=\"content\">\n")
		buffer_html.write("<ul>\n")

		for item in fetch_func():
			link: str = CollectBotTemplate.html_wrapper("a", item['title'], {"href": item['link']})
			list_item: str = CollectBotTemplate.html_wrapper("li", link)
			buffer_html.write(list_item)
			buffer_html.write("\n")

		buffer_html.write("</ul>\n")
		buffer_html.write("</div>\n")
		buffer_html.write("</div>\n")

		return buffer_html.getvalue()

	def auctions_to_html(ebay: EBayAuctions, exclude: list[str]) -> str:
		bufauct: StringIO = StringIO()
		bufauct.write(CollectBotTemplate.make_section_header("Auctions"))

		bufsecs: StringIO = StringIO()
		for auction in ebay.auctions:

			bufsec: StringIO = StringIO()
			bufsec.write(CollectBotTemplate.make_item_header(auction['title']))
			html_: str = ebay._search_results_to_html(
				items=auction['items'],
				epn_category=auction['epn-category'],
				exclude=exclude)
			bufsec.write(CollectBotTemplate.make_content(html_))
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
		return processor.get_content()
	
	def create_html_footer() -> str:
		with open('templates/footer.html', 'r', encoding="utf-8") as file:
			return file.read()

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
	def make_lead_headline(s: str) -> str:
		return markdown.markdown(s, extensions=['attr_list'])

	@_adorner.html_wrapper_attributes("div", {"id": "auctions"})
	def make_auctions(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"id": "news"})
	def make_news(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "container"})
	def make_container(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "section"})
	def make_section(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "content"})
	def make_content(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "section-header"})
	@_adorner.html_wrapper_attributes("h2", {"class": "h2"})
	def make_section_header(s: str) -> str: return s

	@_adorner.html_wrapper_attributes("div", {"class": "item-header"})
	@_adorner.html_wrapper_attributes("h3", {"class": "h3"})
	def make_item_header(s: str) -> str:
		return s

	@_adorner.html_wrapper_attributes("h3", {"class": "h3"})
	def make_h3(s: str) -> str: return s
