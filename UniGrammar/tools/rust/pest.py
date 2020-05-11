import typing
from pathlib import Path

import inflection
from escapelib import CompositeEscaper, backslashUHexEscaper, closingSquareBracketEscaper, commonCharsEscaper, doubleTickEscaper
from UniGrammarRuntime.backends.rust.pest import PestParserFactory, masterBranchURI
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


class PestRunner(NotYetImplementedRunner):
	__slots__ = ()

	COMPILER = DummyCompiler
	PARSER = PestParserFactory

	def __init__(self):
		raise NotImplementedError()

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


# (e) 	matches e
# e1 ~ e2 	matches the sequence e1 e2
# e1 | e2 	matches either e1 or e2
# e* 	matches e zero or more times
# e+ 	matches e one or more times
# e{n} 	matches e exactly n times
# e{, n} 	matches e at most n times
# e{n,} 	matches e at least n times
# e{m, n} 	matches e between m and n times inclusively
# e? 	optionally matches e
# &e 	matches e without making progress
# !e 	matches if e doesn't match without making progress
# PUSH(e) 	matches e and pushes it's captured string down the stack


class Pest(Tool):
	RUNNER = PestRunner

	class GENERATOR(SectionedGenerator):
		META = DSLMetadata(
			officialLibraryRepo=masterBranchURI + "/examples",
			grammarExtensions=("Pest",),
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
			return transformNameForPest(obj.name)

		@classmethod
		def _Name(cls, k: str, v: str, ctx: typing.Any = None) -> str:
			return super()._Name(transformNameForPest(k), v, ctx)
