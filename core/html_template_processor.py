
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import logging

from io import StringIO

logger = logging.getLogger(__name__)

class HtmlTemplateProcessor:
	def __init__(self, template_path: str):
		self._template_path: str = template_path
		self._buffer: StringIO = StringIO(self._load_template())

	def __del__(self):
		self._template_path = None
		self._buffer.seek(0)
		self._buffer.truncate(0)
		self._buffer.close()

	def _load_template(self) -> str:
		"""Load the HTML template into a buffer."""
		with open(self._template_path, 'r') as file:
			return file.read()

	def _load_content_from_file(self, file_path: str) -> str:
		"""Load content from a given file."""
		with open(file_path, 'r') as file:
			return file.read()

	def replace_placeholder(self, placeholder: str, replacement_content: str):
		"""Replace a placeholder in the buffer with the given replacement content."""
		# Create a new StringIO object to hold the modified content
		new_buffer = StringIO()
		placeholder_pattern = '{{' + placeholder + '}}'
		
		# Read and replace
		self._buffer.seek(0)
		for line in self._buffer:
			if placeholder_pattern in line:
				line = line.replace(placeholder_pattern, replacement_content)
			new_buffer.write(line)
		
		# Reset the buffer to the new content
		self._buffer.seek(0)
		self._buffer.truncate(0)
		self._buffer.write(new_buffer.getvalue())
		new_buffer.seek(0)
		new_buffer.truncate(0)
		new_buffer.close()

	def replace_from_file(self, placeholder: str, file_path: str):
		"""Replace a placeholder in the buffer with content loaded from another file."""
		replacement_content = self._load_content_from_file(file_path)
		if file_path.endswith('.css'):
			replacement_content = HtmlTemplateProcessor.minify_css(replacement_content)
		self.replace_placeholder(placeholder, replacement_content)

	def save(self, output_path: str):
		"""Save the processed HTML to a file."""
		with open(output_path, 'w') as file:
			file.write(self._buffer.getvalue())
	
	def get_content(self) -> str:
		"""Get the processed HTML content."""
		self._buffer.seek(0)
		return self._buffer.getvalue()
	
	def minify_css(css_content: str) -> str:
		"""Minify CSS content by removing whitespace and newlines."""
		css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
		css_content = re.sub(r'\s+', ' ', css_content)
		css_content = re.sub(r'\s*([{}:;,])\s*', r'\1', css_content)
		css_content = re.sub(r'url\(\s*([\'"]?[^\'")\s]+[\'"]?)\s*\)', r'url(\1)', css_content)
		return css_content.strip()

if __name__ == "__main__":
	import sys

	def _test():
		with open("templates/style.css", "r") as file:
			style_content: str = HtmlTemplateProcessor.minify_css(file.read())
			print(style_content)

		processor: HtmlTemplateProcessor = HtmlTemplateProcessor("templates/header.html")
		processor.replace_from_file("style_inline", "templates/style_inline.css")
		processor.replace_from_file("header_js", "templates/header_js.html")
		print(processor.get_content())

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
