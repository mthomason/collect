#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import StringIO
from dataclasses import dataclass, field, asdict

@dataclass
class GptFunctionItemProperty:
	name: str
	type: str
	description: str

	@classmethod
	def from_dict(cls, name: str, p: dict[str, str]) -> 'GptFunctionItemProperty':
		return cls(
			name=name,
			type=p["type"],
			description=p["description"]
		)

	def to_dict(self) -> dict[str, str]:
		return { "type": self.type, "description": self.description }

@dataclass
class GptFunctionItems:
	type: str
	required: list[str] = field(default_factory=list)
	properties: dict[str, GptFunctionItemProperty] = field(default_factory=dict)

	@classmethod
	def from_dict(cls, f: dict[str, any]) -> 'GptFunctionItems':
		properties = {r: GptFunctionItemProperty.from_dict(r, f["properties"][r]) for r in f["required"]}
		return cls(
			type=f["type"],
			required=f["required"],
			properties=properties
		)

	def to_dict(self) -> dict[str, any]:
		properties: dict[str, dict[str, str]] = {}
		for name, prop in self.properties.items():
			properties[name] = prop.to_dict()
		return {
			"type": self.type,
			"required": self.required,
			"properties": properties
		}

@dataclass
class GptFunctionProperty:
	name: str
	type: str
	description: str
	items: GptFunctionItems
	
	@classmethod
	def from_dict(cls, name: str, p: dict[str, any]) -> 'GptFunctionProperty':
		return cls(
			name=name,
			type=p["type"],
			description=p["description"],
			items=GptFunctionItems.from_dict(p["items"])
		)

	def to_dict(self) -> dict[str, any]:
		return {
			"type": self.type,
			"description": self.description,
			"items": self.items.to_dict()
		}

@dataclass
class GptFunctionParams:
	type: str
	required: list[str] = field(default_factory=list)
	properties: dict[str, GptFunctionProperty] = field(default_factory=dict)

	@classmethod
	def from_dict(cls, data: dict[str, any]) -> 'GptFunctionParams':
		properties: dict[str, GptFunctionProperty] = {}
		for name, prop in data["properties"].items():
			properties[name] = GptFunctionProperty.from_dict(
				name=name,
				p=prop
			)
		return cls(
			type=data["type"],
			required=data["required"],
			properties=properties
		)

	def to_dict(self) -> dict[str, any]:
		properties: dict[str, dict[str, any]] = {}
		for name, prop in self.properties.items():
			properties[name] = prop.to_dict()
		return {
			"type": self.type,
			"required": self.required,
			"properties": properties
		}

@dataclass
class GptFunction:
	name: str
	description: str
	parameters: GptFunctionParams
	
	@classmethod
	def from_dict(cls, data: dict[str, any]) -> 'GptFunction':
		return cls(
			name=data["name"],
			description=data["description"],
			parameters=GptFunctionParams.from_dict(data["parameters"])
		)

	def to_dict(self) -> dict[str, any]:
		return {
			"name": self.name,
			"description": self.description,
			"parameters": self.parameters.to_dict()
		}

@dataclass
class GptFunctionPrompt:
	name: str
	context: str
	prompt: str
	function: GptFunction

	@classmethod
	def from_dict(cls, data: dict[str, any]) -> 'GptFunctionPrompt':
		return cls(
			name=data["name"],
			context=data["context"],
			prompt=data["prompt"],
			function=GptFunction.from_dict(data["function"])
		)

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
