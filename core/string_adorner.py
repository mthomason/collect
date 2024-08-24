#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import StringIO
from typing import Callable

class HtmlWrapper:
	@staticmethod
	def wrap_html(content: str, tag: str, attributes: dict[str, str] = {}) -> str:
		_buffer = StringIO()
		_buffer.seek(0)
		_buffer.truncate(0)
		_buffer.write("<")
		_buffer.write(tag)
		if len(attributes) > 0:
			for key, value in attributes.items():
				_buffer.write(" ")
				_buffer.write(key)
				_buffer.write("=\"")
				_buffer.write(value)
				_buffer.write("\"")
				
		_buffer.write(">")
		_buffer.write(content)
		_buffer.write("</")
		_buffer.write(tag)
		_buffer.write(">")
		content: str = _buffer.getvalue()
		_buffer.seek(0)
		_buffer.truncate(0)
		_buffer.close()
		return content

	@staticmethod
	def html_item(tag: str, attributes: dict[str, str] = {}):
		_buffer = StringIO()
		if len(attributes) == 0:
			_buffer.write("<")
			_buffer.write(tag)
			_buffer.write(">")
		else:
			_buffer.write("<")
			_buffer.write(tag)
			for key, value in attributes.items():
				_buffer.write(" ")
				_buffer.write(key)
				_buffer.write("=\"")
				_buffer.write(value)
				_buffer.write("\"")
			_buffer.write(">")
		s: str = _buffer.getvalue()
		_buffer.seek(0)
		_buffer.truncate(0)
		_buffer.close()
		return s

class StringAdorner:

	@staticmethod
	def wrap_html(tag: str, attributes: dict[str, str] = {}) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				original_output = func(*args, **kwargs)
				return HtmlWrapper.wrap_html(original_output, tag, attributes)
			return wrapper
		return decorator

	def html_wrapper(self, tag: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				_buffer = StringIO()
				original_output = func(*args, **kwargs)
				_buffer.write("<")
				_buffer.write(tag)
				_buffer.write(">")
				_buffer.write(original_output)
				_buffer.write("</")
				_buffer.write(tag)
				_buffer.write(">")
				s: str = _buffer.getvalue()
				_buffer.seek(0)
				_buffer.truncate(0)
				_buffer.close()
				return s
			return wrapper
		return decorator

	def html_wrapper_attributes(self, tag: str, attributes: dict[str, str]) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				_buffer = StringIO()
				original_output = func(*args, **kwargs)
				_buffer.seek(0)
				_buffer.truncate(0)
				_buffer.write("<")
				_buffer.write(tag)
				if len(attributes) > 0:
					for key, value in attributes.items():
						_buffer.write(" ")
						_buffer.write(key)
						_buffer.write("=\"")
						_buffer.write(value)
						_buffer.write("\"")
				
				_buffer.write(">")
				_buffer.write(original_output)
				_buffer.write("</")
				_buffer.write(tag)
				_buffer.write(">")
				s: str = _buffer.getvalue()
				_buffer.seek(0)
				_buffer.truncate(0)
				_buffer.close()
				return s
			return wrapper
		return decorator
	
	def html_wrapper_attributes_without_stringio(self, tag: str, attributes: dict[str, str]) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				original_output = func(*args, **kwargs)
				attributes_string = "".join(
					f' {key}="{value}"' for key, value in attributes.items()
				)
				s = f"<{tag}{attributes_string}>{original_output}</{tag}>"
				return s
			return wrapper
		return decorator

if __name__ == "__main__":
	import sys

	def _profile():
		import tracemalloc
		import timeit

		def mock_function() -> str:
			return "Hello, World!"

		attributes = {"class": "my-class", "id": "my-id"}
		tag = "div"

		sa: StringAdorner = StringAdorner()

		def version_with_stringio():
			decorator = sa.html_wrapper_attributes(tag, attributes)
			wrapped_func = decorator(mock_function)
			return wrapped_func()

		def version_without_stringio():
			decorator = sa.html_wrapper_attributes_without_stringio(tag, attributes)
			wrapped_func = decorator(mock_function)
			return wrapped_func()

		# Timing
		time_with_stringio = timeit.timeit(version_with_stringio, number=100000)
		time_without_stringio = timeit.timeit(version_without_stringio, number=100000)

		print(f"Time with StringIO: {time_with_stringio:.6f} seconds")
		print(f"Time without StringIO: {time_without_stringio:.6f} seconds")

		# Memory usage
		tracemalloc.start()
		version_with_stringio()
		current, peak_with_stringio = tracemalloc.get_traced_memory()
		tracemalloc.stop()

		tracemalloc.start()
		version_without_stringio()
		current, peak_without_stringio = tracemalloc.get_traced_memory()
		tracemalloc.stop()

		print(f"Peak memory usage with StringIO: {peak_with_stringio} bytes")
		print(f"Peak memory usage without StringIO: {peak_without_stringio} bytes")

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_profile()
	else:
		raise ValueError("This script is not meant to be run directly.")

