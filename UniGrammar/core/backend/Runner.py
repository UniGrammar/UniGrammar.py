import typing
from abc import ABC, abstractmethod
from pathlib import Path

from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources, ParserBundle
from UniGrammarRuntime.ToolMetadata import ToolMetadata

from .Generator import TranspiledResult


class Runner(ABC):
	__slots__ = ()

	COMPILER = None
	PARSER = None  # type: typing.Type[UniGrammarRuntimeCore.IParser.IParserFactory]

	def __init__(self) -> None:
		pass

	def saveCompiled(self, internalRepr: str, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target: str = "python"):
		grammarResources.parent.backendsTextData[meta.product.name, grammarResources.name + "." + meta.mainExtension] = internalRepr

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class NotYetImplementedRunner(Runner):
	__slots__ = ()

	def __init__(self):
		NotImplementedError("Not yet implemented")

	def compileAndSave(self, internalRepr, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target=None):
		raise NotImplementedError("Not yet implemented")

	def trace(self, parser, text: str):
		raise NotImplementedError("Not yet implemented")

	def visualize(self, parser, text: str):
		raise NotImplementedError("Not yet implemented")
