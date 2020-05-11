import typing
from pathlib import Path

try:
	from antlrCompile import ANTLR as ANTLRCompileANTLR
	from antlrCompile import Vis as ANTLRCompileVis
	from antlrCompile.core import ANTLRParser
except ImportError:
	from UniGrammarRuntime.backends.multilanguage.antlr4 import ANTLRDummy as ANTLRCompileANTLR, ANTLRCompileDummy as ANTLRCompileVis, ANTLRDummy as ANTLRParser

from escapelib import CompositeEscaper, closingSquareBracketEscaper, commonEscaper, singleTickEscaper
from UniGrammarRuntime.backends.multilanguage.antlr4 import ANTLRParserFactory, languagesRemap, toolGithubOrg
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata

from ...core.ast import Grammar, Spacer
from ...core.ast.characters import CharClass, CharClassUnion
from ...core.backend.Generator import TranspiledResult
from ...core.backend.Runner import Runner
from ...core.backend.SectionedGenerator import SectionedGenerator, Sectioner
from ...core.backend.Tool import Tool
from ...core.CharClassProcessor import CharClassKeepProcessor

ourCharClassEscaper = CompositeEscaper(commonEscaper, closingSquareBracketEscaper)
ourStringEscaper = CompositeEscaper(commonEscaper, singleTickEscaper)


class ANTLR(ANTLRCompileANTLR):
	__slots__ = ()

	def compileStr(self, grammarText: str, target: str = "python", fileName: typing.Optional[typing.Union[Path, str]] = None):
		return super().compileStr(grammarText, languagesRemap[target], fileName)


class ANTLRGenerator(SectionedGenerator):
	charClassEscaper = ourCharClassEscaper
	stringEscaper = ourStringEscaper

	META = DSLMetadata(
		officialLibraryRepo=toolGithubOrg + "/grammars-v4",
		grammarExtensions=("g4",),
	)

	assignmentOperator = ": "
	capturingOperator = "="
	endStatementOperator = ";"
	singleLineCommentStart = "//"

	DEFAULT_ORDER = ("prods", "fragmented", "keywords", "tokens", "chars")

	class SECTIONER(Sectioner):
		@classmethod
		def START(cls, backend: SectionedGenerator, gr: Grammar, ctx: typing.Any = None):
			yield from super(cls, cls).START(backend, gr, ctx)
			yield "grammar " + gr.meta.id + backend.endStatementOperator
			yield backend.resolve(Spacer(), gr, ctx)

	@classmethod
	def wrapLiteralString(cls, s: str) -> str:
		return "'" + cls.stringEscaper(s) + "'"

	#@classmethod
	#def wrapLiteralChar(cls, s: str) -> str:
	#	return

	class CHAR_CLASS_PROCESSOR(CharClassKeepProcessor):
		charClassPositiveJoiner = "|"
		charClassSetStart = "["
		charClassSetEnd = "]"

		@classmethod
		def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			#return "ANY" + cls.charClassNegativeJoiner if obj.negative else "" + s
			if obj.negative:
				s = "~" + s

			return s

		@classmethod
		def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			return s

	@classmethod
	def CharClass(cls, obj: CharClass, grammar: Grammar, ctx: typing.Any = None) -> str:
		if len(obj.chars) == 1:
			return cls.wrapLiteralChar(obj.chars)
		return cls.CHAR_CLASS_PROCESSOR.wrapCharClass(cls, cls.escapeCharClassString(obj.chars), obj, grammar)


class ANTLRRunner(Runner):
	__slots__ = ()

	COMPILER = ANTLR
	PARSER = ANTLRParserFactory

	def saveCompiled(self, internalRepr, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target: str = "python"):
		for name, text in internalRepr.asFileNameDict().items():
			grammarResources.parent.backendsTextData[meta.product.name, str(name)] = str(text)

	def execute(self, res):
		return self.__class__.PARSER.fromCompResult(res)

	def parse(self, parser, text: str) -> None:
		return parser(text)

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		v = ANTLRCompileVis()
		window = v.treeGUIVisualization(parser, text, block=False)
		window.setTitle(window.getTitle() + " (from UniGrammar)")
		v.blockOnGUIWindow(window)


class ANTLR(Tool):
	RUNNER = ANTLRRunner
	GENERATOR = ANTLRGenerator
