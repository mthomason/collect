#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import StringIO

class GptFunctionItemProperty:
	def __init__(self, name: str, p: dict[str, any]):
		self._name: str = name
		self._type: str = p["type"]
		self._description: str = p["description"]

	@property
	def name(self) -> str: return self._name

	@property
	def type(self) -> str: return self._type

	@property
	def description(self) -> str: return self._description

	def __str__(self) -> str:
		return f"GptFunctionItemProperty(name={self._name})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunctionItemProperty(\n\t")
		s.write(f"name={self._name},\n\t")
		s.write(f"type={self._type},\n\t")
		s.write(f"description={self._description[0:80]}\n")
		s.write(")\n")
		return s.getvalue()
	
	def to_dict(self) -> dict[str, str]:
		return {
			"type": self._type,
			"description": self._description
		}

class GptFunctionItems:
	def __init__(self, f: dict[str, any]):
		self._type: str = f["type"]
		self._properties: dict[str, GptFunctionItemProperty] = {}
		self._required: list[str] = []
		for r in f["required"]:
			self._required.append(r)
			self._properties[r] = GptFunctionItemProperty(r, f["properties"][r])

	@property
	def type(self) -> str: return self._type

	@property
	def required(self) -> list[str]: return self._required

	@property
	def properties(self) -> dict[str, GptFunctionItemProperty]:
		return self._properties
	
	def __str__(self) -> str:
		return f"GptFunctionItems(type={self._type})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunctionItems(\n\t")
		s.write(f"type={self._type},\n\t")
		s.write(")\n")
		return s.getvalue()
	
	def to_dict(self) -> dict[str, any]:
		properties: dict[str, dict[str, str]] = {}
		for name, prop in self._properties.items():
			properties[name] = prop.to_dict()
		return {
			"type": self._type,
			"required": self._required,
			"properties": properties
		}

class GptFunctionProperty:
	def __init__(self, name: str, p: dict[str, any]):
		self._name: str = name
		self._type: str = p["type"]
		self._description: str = p["description"]
		self._items: GptFunctionItems = GptFunctionItems(p["items"])

	@property
	def name(self) -> str: return self._name

	@property
	def type(self) -> str: return self._type

	@property
	def description(self) -> str: return self._description

	@property
	def items(self) -> GptFunctionItems: return self._items

	def __str__(self) -> str:
		return f"GptFunctionProperty(name={self._name})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunctionProperty(\n\t")
		s.write(f"name={self._name},\n\t")
		s.write(f"type={self._type},\n\t")
		s.write(f"description={self._description[0:80]},\n\t")
		s.write(")\n")
		return s.getvalue()
	
	def to_dict(self) -> dict[str, any]:
		return {
			"type": self._type,
			"description": self._description,
			"items": self._items.to_dict()
		}

class GptFunctionParams:
	def __init__(self, p: dict[str, any]):
		self._type: str = p["type"]
		self._required: list[str] = []
		self._properties: dict[str, GptFunctionProperty] = {}
		for r in p["required"]:
			self._properties[r] = GptFunctionProperty(r, p["properties"][r])
			self._required.append(r)

	@property
	def type(self) -> str: return self._type

	@property
	def required(self) -> list[str]: return self._required

	@property
	def properties(self) -> dict[str, GptFunctionProperty]:
		return self._properties
	
	def __str__(self) -> str:
		return f"GptFunctionParams(type={self._type})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunctionParams(\n\t")
		s.write(f"type={self._type},\n\t")
		s.write(f"required={self.required},\n\t")
		s.write(")\n")
		return s.getvalue()
	
	def to_dict(self) -> dict[str, any]:
		properties: dict[str, dict[str, any]] = {}
		for name, prop in self._properties.items():
			properties[name] = prop.to_dict()
		return {
			"type": self._type,
			"required": self._required,
			"properties": properties
		}

class GptFunction:
	def __init__(self, f: dict[str, any]):
		self._name: str = f["name"]
		self._description: str = f["description"]
		self._parameters: GptFunctionParams = GptFunctionParams(f["parameters"])

	@property
	def name(self) -> str: return self._name

	@property
	def description(self) -> str: return self._description

	@property
	def parameters(self) -> GptFunctionParams: return self._parameters

	def __str__(self) -> str:
		return f"GptFunction(name={self._name})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunction(\n\t")
		s.write(f"name={self._name},\n\t")
		s.write(f"description={self._description[0:80]},\n\t")
		s.write(")\n")
		return s.getvalue()
	
	def to_dict(self) -> dict[str, any]:
		return {
			"name": self._name,
			"description": self._description,
			"parameters": self._parameters.to_dict()
	}

class GptFunctionPrompt:
	def __init__(self, prompt: dict[str, any]):
		self._name: str = prompt["name"]
		self._context: str = prompt["context"]
		self._prompt: str = prompt["prompt"]
		self._function: GptFunction = GptFunction(prompt["function"])

	@property
	def name(self) -> str: return self._name

	@property
	def context(self) -> str: return self._context

	@property
	def prompt(self) -> str: return self._prompt
	
	@property
	def function(self) -> GptFunction: return self._function

	def __str__(self) -> str:
		return f"GptFunctionPrompt(name={self._name})"
	
	def __repr__(self) -> str:
		s: StringIO = StringIO()
		s.write("GptFunctionPrompt(\n\t")
		s.write(f"name={self._name},\n\t")
		s.write(f"context={self._context[0:80]},\n\t")
		s.write(f"prompt={self._prompt[0:80]},\n\t")
		s.write(f"function={self._function}\n")
		s.write(")\n")
		return s.getvalue()

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
