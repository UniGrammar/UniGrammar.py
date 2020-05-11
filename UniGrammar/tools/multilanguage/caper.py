import typing
from pathlib import Path

from UniGrammarRuntime.backends.multilanguage.caper import CaperParserFactory
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import PEG
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.backend.Runner import Runner
from ...core.backend.Tool import Tool
from ..core.CharClassProcessor import CharClassMergeProcessor
from ..generators.packrat import PackratGenerator


class CaperRunner(Runner):
	__slots__ = ("PG",)

	COMPILER = DummyCompiler
	PARSER = CaperParserFactory

	def __init__(self):
		from caper.grammar import Grammar

		self.PG = Grammar

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class CaperGenerator(PackratGenerator):
	META = DSLMetadata(
		officialLibraryRepo=None,
		grammarExtensions=None,
	)

	assignmentOperator = " = "
	singleLineCommentStart = "#"


class Caper(Tool):
	RUNNER = CaperRunner
	GENERATOR = CaperGenerator
