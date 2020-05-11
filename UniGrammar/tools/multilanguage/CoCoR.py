import typing

from escapelib import CompositeEscaper, UnicodeEscaper, commonCharsEscaper, doubleTickEscaper
from UniGrammarRuntime.backends.multilanguage.CoCoR import CoCoRParser, CoCoRParserFactory
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import LL
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.ast import Comment, Grammar, Spacer
from ...core.ast.base import Name, Ref
from ...core.ast.characters import CharClass, CharClassUnion
from ...core.ast.transformations import getReferenced, rewriteReferences
from ...core.backend.Runner import NotYetImplementedRunner, Runner
from ...core.backend.SectionedGenerator import SectionDumper, SectionedGenerator, SectionedGeneratorContext, Sectioner
from ...core.backend.Tool import Tool
from ...core.CharClassProcessor import CharClassKeepProcessor

backslashXHexEscaper = UnicodeEscaper("\\x{}", stringizer="uhex")

ourStringEscaper = CompositeEscaper(commonCharsEscaper, doubleTickEscaper, backslashXHexEscaper)


class CoCoRGeneratorContext(SectionedGeneratorContext):
	__slots__ = ("nameRemap",)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.charClassesToTokensNameRemap = {}


class CoCoRRunner(NotYetImplementedRunner):
	COMPILER = DummyCompiler
	PARSER = CoCoRParserFactory


class CoCoR(Tool):
	RUNNER = CoCoRRunner

	class GENERATOR(SectionedGenerator):
		META = DSLMetadata(
			officialLibraryRepo=None,
			grammarExtensions=("atg",),
		)

		charClassEscaper = ourStringEscaper
		stringEscaper = ourStringEscaper

		assignmentOperator = " = "
		endStatementOperator = "."
		singleLineCommentStart = "//"
		multiLineCommentStart = "/*"
		multiLineCommentEnd = "*/"

		DEFAULT_ORDER = ("chars", "keywordsAndCharsTokens", "tokens", "productionsKeyword", "keywords", "fragmented", "firstRule", "prods")

		@classmethod
		def initContext(cls, grammar):
			return CoCoRGeneratorContext(None)

		class SECTIONER(Sectioner):
			@classmethod
			def START(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
				yield from super(cls, cls).START(backend, gr)
				yield "COMPILER " + gr.meta.id
				yield backend.resolve(Spacer(), gr)

			class chars(SectionDumper):
				__slots__ = ()

				@classmethod
				def dumpSection(self, backend: SectionedGenerator, gr: Grammar, content: typing.Iterable[str], ctx: typing.Any = None):
					if content:
						yield "CHARACTERS"
						yield from content
						yield backend.resolve(Spacer(2), gr, ctx)

				@classmethod
				def dumpContent(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
					charsReferencedInTokens = getReferenced(gr.tokens)

					for charSymbol in gr.chars.children:
						if isinstance(charSymbol, Name):
							tokenName = charSymbol.name
							if tokenName not in charsReferencedInTokens:
								ctx.charClassesToTokensNameRemap[tokenName] = charSymbol.name = charSymbol.name + "C"

					rewriteReferences(gr.chars, ctx.charClassesToTokensNameRemap)
					yield from Sectioner.chars.dumpContent(backend, gr, ctx)

			class keywordsAndCharsTokens(SectionDumper):
				__slots__ = ()

				@classmethod
				def dumpSection(self, backend: SectionedGenerator, gr: Grammar, content: typing.Iterable[str], ctx: typing.Any = None):
					if content:
						yield "TOKENS"
						yield backend.resolve(Comment("character tokens"), gr, ctx)
						yield from content
						yield backend.resolve(Spacer(2), gr, ctx)

				@classmethod
				def dumpContent(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
					for tokenName, charName in ctx.charClassesToTokensNameRemap.items():
						yield backend.resolve(Name(tokenName, Ref(charName)), gr, ctx)

			@classmethod
			def productionsKeyword(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
				yield "PRODUCTIONS"

			@classmethod
			def firstRule(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
				if gr.meta:
					yield backend.resolve(Name(gr.meta.id, gr.prods.findFirstRule().name), gr, ctx)

			@classmethod
			def END(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
				yield "END " + gr.meta.id + " " + backend.endStatementOperator

		class CHAR_CLASS_PROCESSOR(CharClassKeepProcessor):
			charClassNegativeJoiner = "-"
			charClassPositiveJoiner = "+"
			charClassSetStart = '"'
			charClassSetEnd = '"'

			@classmethod
			def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
				return "ANY" + cls.charClassNegativeJoiner if obj.negative else "" + s

			@classmethod
			def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
				return s

		@classmethod
		def wrapOneOrMore(cls, *args, **kwargs):
			return cls.wrapNOrMore(1, *args, **kwargs)

		@classmethod
		def wrapZeroOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
			return "{" + res + "}"

		@classmethod
		def wrapZeroOrOne(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
			return "[" + res + "]"
