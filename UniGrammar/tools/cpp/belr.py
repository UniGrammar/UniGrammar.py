import typing
from pathlib import Path

import inflection
from escapelib import CompositeEscaper, backslashUHexEscaper, closingSquareBracketEscaper, commonCharsEscaper, doubleTickEscaper
from UniGrammarRuntime.backends.cpp.belr import BeLRParserFactory, masterBranchURI
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
from ...core.CharClassProcessor import CharClassMergeProcessor
from ...generators.pythonicGenerator import PythonicGenerator

charClassEscaper = CompositeEscaper(commonCharsEscaper, closingSquareBracketEscaper, backslashUHexEscaper)


class BeLRRunner(NotYetImplementedRunner):
	__slots__ = ()

	COMPILER = DummyCompiler
	PARSER = BeLRParserFactory

	def __init__(self):
		raise NotImplementedError()

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class BeLR(Tool):
	RUNNER = BeLRRunner

	class GENERATOR(SectionedGenerator):
		META = DSLMetadata(
			officialLibraryRepo=masterBranchURI + "/examples",
			grammarExtensions=("BeLR",),
		)
		escaper = charClassEscaper

		assignmentOperator = " = "
		endStatementOperator = ""
		singleLineCommentStart = "#"

		DEFAULT_ORDER = ("firstRule", "prods", "fragmented", "keywords", "chars", "tokens")

		charClassEscaper = pythonRegexEscaper

		class CHAR_CLASS_PROCESSOR(CharClassMergeProcessor):
			charClassSetStart = "["
			charClassSetEnd = "]"

			@classmethod
			def encloseCharClass(cls, s: str, obj: _CharClass, grammar: Grammar) -> str:
				return "/" + cls.charClassSetStart + s.replace("/", r"\/") + cls.charClassSetEnd + "/"

		class SECTIONER(SectionedGenerator.SECTIONER):
			@classmethod
			def firstRule(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
				if gr.meta:
					yield backend.resolve(Name("start", gr.prods.findFirstRule().name), gr, ctx)

		@classmethod
		def wrapLiteralString(cls, s: str) -> str:
			return '"' + doubleTickEscaper(s) + '"'

		@classmethod
		def Ref(cls, obj, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
			return transformNameForBeLR(obj.name)

		@classmethod
		def _Name(cls, k: str, v: str, ctx: typing.Any = None) -> str:
			return super()._Name(transformNameForBeLR(k), v, ctx)
