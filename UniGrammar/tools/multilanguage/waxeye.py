import typing
from pathlib import Path

from escapelib import CompositeEscaper, backslashUHexEscaper, closingSquareBracketEscaper, commonCharsEscaper
from UniGrammarRuntime.backends.multilanguage.waxeye import WaxeyeParserFactory, masterBranchURI
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.ast import Grammar
from ...core.ast.characters import CharClass, CharClassUnion
from ...core.backend.Generator import TranspiledResult
from ...core.backend.Runner import NotYetImplementedRunner, Runner
from ...core.backend.SectionedGenerator import SectionedGenerator
from ...core.backend.Tool import Tool
from ...core.CharClassProcessor import CharClassMergeProcessor

charClassEscaper = CompositeEscaper(commonCharsEscaper, closingSquareBracketEscaper, backslashUHexEscaper)


class WaxeyeRunner(Runner):
	__slots__ = ("waxeye", "MempipedPathRead")

	COMPILER = DummyCompiler
	PARSER = WaxeyeParserFactory

	def __init__(self):
		import sh
		from MempipedPath import MempipedPathRead

		self.MempipedPathRead = MempipedPathRead

		self.waxeye = sh.Command("./bin/waxeye").bake(_fg=True)

	# ToDO: -i : Interpret, -t <test> : Test

	def _waxeyeGenerate(self, internalRepr, nameSpace: str, language: str, outDir: Path):
		outDir.mkdir(exist_ok=True, parents=True)
		with self.MempipedPathRead(internalRepr) as f:
			#"-m"
			# "-c", "Generated with UniGrammar"
			#"--debug"
			self.waxeye("-n", nameSpace, "-p", nameSpace, "-g", language, outDir, f)

	def saveCompiled(self, internalRepr, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target: str = "python"):
		parentDir = grammarResources.parent.bundleDir / "compiled" / meta.product.name
		self._waxeyeGenerate(internalRepr, grammarResources.name, "python", parentDir)

	def execute(self, g: typing.Any) -> typing.Any:
		raise NotImplementedError()

	def parse(self, parser: "parglare.parser.Parser", text: str) -> None:
		raise NotImplementedError()

	def trace(self, parser: "parglare.parser.Parser", text: str):
		raise NotImplementedError()

	def visualize(self, parser: "parglare.parser.Parser", text: str):
		raise NotImplementedError()


class WaxeyeGenerator(SectionedGenerator):
	META = DSLMetadata(
		officialLibraryRepo=masterBranchURI + "/grammars",
		grammarExtensions=("waxeye",),
	)
	escaper = charClassEscaper

	assignmentOperator = " <- "
	endStatementOperator = ""
	singleLineCommentStart = "#"

	DEFAULT_ORDER = ("prods", "fragmented", "keywords", "chars", "tokens")

	class CHAR_CLASS_PROCESSOR(CharClassMergeProcessor):
		charClassSetStart = "["
		charClassSetEnd = "]"

		@classmethod
		def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			return ("!" if obj.negative else "") + s

		@classmethod
		def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			return s

	@classmethod
	def wrapZeroOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "*" + res

	@classmethod
	def wrapOneOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "+" + res

	@classmethod
	def wrapZeroOrOne(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "?" + res


class Waxeye(Tool):
	GENERATOR = WaxeyeGenerator
	RUNNER = WaxeyeRunner
