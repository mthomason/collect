#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import StringIO
from typing import Callable

class StringAdorner:

	def md_adornment(self, adornment: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				_buffer = StringIO()
				original_output = func(*args, **kwargs)
				_buffer.write(adornment)
				_buffer.write(original_output)
				_buffer.write(adornment)
				return _buffer.getvalue()
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
				return _buffer.getvalue()
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
				return _buffer.getvalue()
			return wrapper
		return decorator

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
