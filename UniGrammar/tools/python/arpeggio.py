import typing
from pathlib import Path

from UniGrammarRuntime.backends.python.arpeggio import ArpeggioParserFactory, toolGitRepo
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import PEG
from UniGrammarRuntime.IParsingBackend import ToolSpecificGrammarASTWalkStrategy
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, Name, Productions, Spacer, Tokens
from ...core.ast.base import Ref
from ...core.ast.characters import CharClass
from ...core.ast.tokens import Alt, Seq
from ...core.backend.Lifter import Lifter, LiftingContext, LiftingVisitor
from ...core.backend.Runner import Runner
from ...core.backend.Tool import Tool
from ...core.CharClassProcessor import CharClassMergeProcessor
from ...generators.packrat import PackratGenerator, PythonicGenerator


class ArpeggioRunner(Runner):
	__slots__ = ("ParserPEG",)

	COMPILER = DummyCompiler
	PARSER = ArpeggioParserFactory

	def __init__(self):
		from arpeggio.peg import ParserPEG

		self.ParserPEG = ParserPEG

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class ArpeggioGenerator(PackratGenerator):
	META = ArpeggioParserFactory.FORMAT

	assignmentOperator = " <- "
	singleLineCommentStart = "//"
	endStatementOperator = ";"

	class CHAR_CLASS_PROCESSOR(CharClassMergeProcessor):
		charClassSetStart = "r'" + PythonicGenerator.CHAR_CLASS_PROCESSOR.charClassSetStart
		charClassSetEnd = PythonicGenerator.CHAR_CLASS_PROCESSOR.charClassSetEnd + "'"


class ArpeggioLiftingContext(LiftingContext):
	__slots__ = ()


class ArpeggioLifterWalkStrategy(ToolSpecificGrammarASTWalkStrategy):
	__slots__ = ()

	def iterateChildren(self, node):
		"""Gets an iterable of children nodes of tool-specific AST node"""
		return node.nodes

	def isTerminal(self, node):
		"""Returns if a node is a terminal that should not be further iterated"""
		raise NotImplementedError

	def iterateCollection(self, lst) -> typing.Any:
		return lst.nodes

	def isCollection(self, lst: typing.Any) -> bool:
		return hasattr(lst, "nodes")


class ArpeggioVisitor(LiftingVisitor):
	__slots__ = ()

	@classmethod
	def Sequence(cls, l: Lifter, r, ctx):
		return cls._Seq(l, r, ctx)

	@classmethod
	def OrderedChoice(cls, l: Lifter, ps, ctx):
		return cls._Alt(l, ps, ctx)

	@classmethod
	def ZeroOrMore(cls, l: Lifter, s, ctx):
		cls.iter(l, 0, s, ctx)

	@classmethod
	def OneOrMore(cls, l: Lifter, s, ctx):
		return cls.iter(1, s, ctx)

	@classmethod
	def Optional(cls, l: Lifter, s, ctx):
		return cls._Opt(l, s, ctx)

	@classmethod
	def RegExMatch(cls, l: Lifter, s, ctx):
		return cls._regExp(l, s, ctx)

	@classmethod
	def StrMatch(cls, l: Lifter, r, ctx):
		return cls._literal(l, r, ctx)

	@classmethod
	def EOF(cls, l: Lifter, g, ctx):
		pass


class ArpeggioLifter(Lifter):
	CONTEXT_TYPE = ArpeggioLiftingContext
	VISITOR_TYPE = ArpeggioVisitor
	AWALK = ArpeggioLifterWalkStrategy(ArpeggioParserFactory)
	TOOL_GENERATES_ASDAG = True

	def isToken(self, s, isCollection, ctx):
		return isinstance(s, ArpeggioParserFactory.arpeggio.StrMatch)

	def getRegExpSource(self, node, ctx) -> str:
		return r.to_match

	def getTokenText(self, node, ctx) -> str:
		#return r.literal
		return r.to_match

	@classmethod
	def getOriginalIdForAnElement(cls, s, ctx):
		return s.id

	@classmethod
	def setOriginalIdForAnElement(cls, s, ctx, v):
		s.id = v

	def parseToolSpecificGrammarIntoAST(self, grammarText, factory):
		return factory.compileStr(grammarText)

	def transformGrammar(self, ctx: LiftingContext):
		self.makeRefAndInsertIfNeeded(ctx.pg.parser_model, ctx)


class Arpeggio(Tool):
	RUNNER = ArpeggioRunner
	GENERATOR = ArpeggioGenerator
	LIFTER = ArpeggioLifter
