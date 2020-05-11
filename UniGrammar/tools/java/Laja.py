import typing
from pathlib import Path

import inflection
from escapelib import CompositeEscaper, backslashUHexEscaper, closingSquareBracketEscaper, commonCharsEscaper, doubleTickEscaper
from UniGrammarRuntime.backends.java.Laja import LajaParserFactory, masterBranchURI
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import PEG
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.ast import Grammar, Productions
from ...core.ast.base import Name
from ...core.ast.characters import CharClass, CharClassUnion
from ...core.backend.Generator import TranspiledResult
from ...core.backend.Runner import NotYetImplementedRunner, Runner
from ...core.backend.SectionedGenerator import SectionedGenerator
from ...core.backend.Tool import Tool
from ...core.CharClassProcessor import CharClassKeepProcessor
from ...generators.pythonicGenerator import PythonicGenerator

charClassEscaper = CompositeEscaper(commonCharsEscaper, closingSquareBracketEscaper, backslashUHexEscaper)


class LajaRunner(NotYetImplementedRunner):
	__slots__ = ()

	COMPILER = DummyCompiler
	PARSER = LajaParserFactory

	def __init__(self):
		raise NotImplementedError()

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class Laja(Tool):
	RUNNER = LajaRunner

	class GENERATOR(SectionedGenerator):
		META = DSLMetadata(
			officialLibraryRepo=masterBranchURI + "/examples",
			grammarExtensions=("Laja",),
		)
		escaper = charClassEscaper

		assignmentOperator = " = "
		endStatementOperator = ";"
		singleLineCommentStart = "//"

		DEFAULT_ORDER = ("firstRule", "prods", "fragmented", "keywords", "chars", "tokens")

		charClassEscaper = pythonRegexEscaper

		class CHAR_CLASS_PROCESSOR(CharClassKeepProcessor):
			@classmethod
			def encloseCharClass(cls, s: str, obj: _CharClass, grammar: Grammar) -> str:
				raise NotImplementedError()

		@classmethod
		def wrapLiteralString(cls, s: str) -> str:
			raise NotImplementedError()

		@classmethod
		def Ref(cls, obj, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
			raise NotImplementedError()

		@classmethod
		def _Name(cls, k: str, v: str, ctx: typing.Any = None) -> str:
			raise NotImplementedError()
