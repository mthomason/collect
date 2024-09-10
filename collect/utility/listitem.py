#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

from datetime import datetime, timezone
from dataclasses import dataclass
from abc import ABC, abstractmethod, ABCMeta

from .core.string_adorner import StringAdorner, HtmlWrapper
from enum import Enum
from typing import Generator

logger = logging.getLogger(__name__)

class ListType(Enum):
	Unordered = 1
	Ordered = 2
	Description = 3

class ListItem(metaclass=ABCMeta):
	title: str
	value: any
	ltype: ListType

	def gethtml_title(self) -> str:
		match self.ltype:
			case ListType.Unordered | ListType.Ordered:
				return HtmlWrapper.wrap_html(self.title, "b", {})
			case ListType.Description:
				return HtmlWrapper.wrap_html(self.title, "dt", {})
		return self.title
	
	def gethtml_value(self) -> str:
		match self.ltype:
			case ListType.Unordered | ListType.Ordered:
				return HtmlWrapper.wrap_html(self.getvaluestr(), "i", {})
			case ListType.Description:
				return HtmlWrapper.wrap_html(self.getvaluestr(), "dd", {})
		return str(self.value)
	
	def gethtml(self) -> str:
		content: str = self.gethtml_title() + self.gethtml_value()
		match self.ltype:
			case ListType.Unordered | ListType.Ordered:
				return HtmlWrapper.wrap_html(content, "li", {})
			case ListType.Description:
				return content
		return content
	
	def getvaluestr(self) -> str:
		return str(self.value)

	@abstractmethod
	def getstring(self) -> str: pass

class TimeItem(ListItem):

	def __init__(self, title: str, value: datetime,
				 ltype: ListType = ListType.Unordered):
		super().__init__()
		self.title = title
		self.value = value
		self.ltype = ltype

	def title(self) -> str:
		return self.title

	def value(self) -> datetime:
		return self.value

	def gethtml_value(self) -> str:
		match self.ltype:
			case ListType.Unordered | ListType.Ordered:
				return self.getvaluestr()
			case ListType.Description:
				return HtmlWrapper.wrap_html(self.getvaluestr(), "dd", {})
		return str(self.value)

	def getstring(self) -> str:
		return self.value.strftime("%Y-%m-%d %H:%M:%S")

	def getvaluestr(self) -> str:
		return HtmlWrapper.wrap_html(
			self.getstring(),
			"time",
			{
				"id": "last-updated",
				"datetime": self.value.strftime('%Y-%m-%dT%H:%M:%S')
			}
		)

class IntItem(ListItem):
	title: str
	value: int

	def __init__(self, title: str, value: int, ltype: ListType = ListType.Unordered):
		self.title = title
		self.value = value
		self.ltype = ltype

	def title(self) -> str:
		return self.title

	def value(self) -> int:
		return self.value

	def getstring(self) -> str:
		return str(self.value)
	
	def getvaluestr(self) -> str:
		return self.getstring()

class StrItem(ListItem):
	title: str
	value: str

	def __init__(self, title: str, value: str, ltype: ListType = ListType.Unordered):
		self.title = title
		self.value = value
		self.ltype = ltype

	def title(self) -> str:
		return self.title

	def value(self) -> str:
		return self.value

	def getstring(self) -> str:
		return self.value
	
	def getvaluestr(self) -> str:
		return self.value

class LinkItem(ListItem):
	title: str
	value: str

	def __init__(self, title: str, value: str, ltype: ListType = ListType.Unordered):
		self.title = title
		self.value = value
		self.ltype = ltype
		self.attributes = {"href": self.value}

	def add_attribute(self, key: str, value: str):
		self.attributes[key] = value

	def title(self) -> str:
		return self.title

	def value(self) -> str:
		return self.value

	def getstring(self) -> str:
		return self.value
	
	def gethtml(self) -> str:
		content: str = HtmlWrapper.wrap_html(self.title, "a", self.attributes)
		match self.ltype:
			case ListType.Unordered | ListType.Ordered:
				return HtmlWrapper.wrap_html(content, "li", {})
			case ListType.Description:
				return HtmlWrapper.wrap_html(content, "dd", {})

	def gethtml_value(self) -> str:
		return HtmlWrapper.wrap_html(self.value, "a", self.attributes)
	
	def getvaluestr(self) -> str:
		return HtmlWrapper.wrap_html(self.title, "a", self.attributes)

class ListItemsCollection:
	items: list[ListItem]
	ltype: ListType

	def __init__(self, items: list[ListItem] = [],
				 ltype: ListType = ListType.Unordered):
		self.items = items
		self.ltype = ltype

	def __len__(self) -> int:
		return len(self.items)
	
	def __getitem__(self, index: int) -> ListItem:
		return self.items[index]
					
	def __setitem__(self, index: int, value: ListItem):
		self.items[index] = value
	
	def __delitem__(self, index):
		del self._list[index]
	
	def __iter__(self) -> Generator[ListItem, None, None]:
		for item in self.items:
			yield item
	
	def __reversed__(self) -> Generator[ListItem, None, None]:
		for item in reversed(self.items):
			yield item
	
	def additem(self, item: ListItem):
		self.items.append(item)

	def append(self, item: ListItem):
		self.items.append(item)
	
	def extend(self, items: list[ListItem]):
		self.items.extend(items)
	
	def remove(self, item: ListItem):
		self.items.remove(item)

	def __repr__(self) -> str:
		return f"{self.__class__.__name__}({self.items})"

	def getstring(self) -> str:
		_buffer = []
		for item in self.items:
			_buffer.append(item.getstring())
		return "\n".join(_buffer)

	def gethtml(self) -> str:
		_buffer = []
		for item in self.items:
			item.ltype = self.ltype
			_buffer.append(item.gethtml())
		return "\n".join(_buffer)

class UnorderedList(ListItemsCollection):
	def __init__(self, items: list[ListItem] = []):
		super().__init__(items)
		self.ltype = ListType.Unordered
	
	@StringAdorner.wrap_html("ul", {})
	def gethtml(self) -> str:
		return super().gethtml()

class DescriptionList(ListItemsCollection):
	def __init__(self, items: list[ListItem] = []):
		super().__init__(items)
		self.ltype = ListType.Description
	
	@StringAdorner.wrap_html("dl", {})
	def gethtml(self) -> str:
		return super().gethtml()

if __name__ == '__main__':
	raise("This module is not meant to be run as a script.")
