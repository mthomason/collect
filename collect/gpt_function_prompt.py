#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field

@dataclass
class GptFunctionItemProperty:
	name: str
	type: str
	description: str

	def to_dict(self) -> dict[str, str]:
		return { "type": self.type, "description": self.description }

@dataclass
class GptFunctionItems:
	type: str
	required: list[str] = field(default_factory=list)
	properties: dict[str, GptFunctionItemProperty] = field(default_factory=dict)

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
		properties = {
			name: GptFunctionProperty(
				name=name,
				type=prop["type"],
				description=prop["description"],
				items=GptFunctionItems(
					type=prop["items"]["type"],
					required=prop["items"]["required"],
					properties={
						r: GptFunctionItemProperty(
							name=r,
							type=prop["items"]["properties"][r]["type"],
							description=prop["items"]["properties"][r]["description"]
						) for r in prop["items"]["required"]
					}
				)
			)
			for name, prop in data["function"]["parameters"]["properties"].items()
		}

		params = GptFunctionParams(
			type=data["function"]["parameters"]["type"],
			required=data["function"]["parameters"]["required"],
			properties=properties
		)

		function = GptFunction(
			name=data["function"]["name"],
			description=data["function"]["description"],
			parameters=params
		)

		return cls(
			name=data["name"],
			context=data["context"],
			prompt=data["prompt"],
			function=function
		)

if __name__ == "__main__":
	raise ValueError("This script is not meant to be run directly.")
