# /collect/string_adorner.py
# -*- coding: utf-8 -*-

from io import StringIO
from typing import Callable

class StringAdorner:
	def __init__(self):
		self._buffer = StringIO()

	def md_adornment(self, adornment: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				self._buffer.seek(0)
				self._buffer.truncate(0)
				original_output = func(*args, **kwargs)
				self._buffer.write(adornment)
				self._buffer.write(original_output)
				self._buffer.write(adornment)
				return self._buffer.getvalue()
			return wrapper
		return decorator

	def html_wrapper(self, tag: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				original_output = func(*args, **kwargs)
				self._buffer.seek(0)
				self._buffer.truncate(0)
				self._buffer.write("<")
				self._buffer.write(tag)
				self._buffer.write(">")
				self._buffer.write(original_output)
				self._buffer.write("</")
				self._buffer.write(tag)
				self._buffer.write(">")
				return self._buffer.getvalue()
			return wrapper
		return decorator

	def html_wrapper_attributes(self, tag: str, attributes: dict[str, str]) -> Callable[[Callable[..., str]], Callable[..., str]]:
		def decorator(func: Callable[..., str]) -> Callable[..., str]:
			def wrapper(*args: any, **kwargs: any) -> str:
				original_output = func(*args, **kwargs)
				self._buffer.seek(0)
				self._buffer.truncate(0)
				self._buffer.write("<")
				self._buffer.write(tag)
				for key, value in attributes.items():
					self._buffer.write(" ")
					self._buffer.write(key)
					self._buffer.write("=")
					self._buffer.write("\"")
					self._buffer.write(value)
					self._buffer.write("\"")
				self._buffer.write(">")
				self._buffer.write(original_output)
				self._buffer.write("</")
				self._buffer.write(tag)
				self._buffer.write(">")
				return self._buffer.getvalue()
			return wrapper
		return decorator

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
