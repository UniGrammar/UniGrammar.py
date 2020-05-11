import typing
from pathlib import Path

from UniGrammarRuntime.backends.python.parsimonious import ParsimoniousParserBackendWalkStrategy, ParsimoniousParserFactory
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
from ...generators.packrat import PackratGenerator


class ParsimoniousRunner(Runner):
	__slots__ = ("PG",)

	COMPILER = DummyCompiler
	PARSER = ParsimoniousParserFactory

	def __init__(self):
		from parsimonious.grammar import Grammar

		self.PG = Grammar

	def trace(self, parser, text: str):
		raise NotImplementedError()

	def visualize(self, parser, text: str):
		raise NotImplementedError()


class ParsimoniousGenerator(PackratGenerator):
	META = ParsimoniousParserFactory.FORMAT

	assignmentOperator = " = "
	singleLineCommentStart = "#"
	endStatementOperator = ""


class ParsimoniousLiftingContext(LiftingContext):
	__slots__ = ()


class ParsimoniousParserBackendWalkStrategy(ToolSpecificGrammarASTWalkStrategy):
	__slots__ = ()

	def iterateChildren(self, node):
		return node.members

	def isTerminal(self, node):
		return isinstance(node, self.parserFactory.parsimonious.nodes.RegexNode)

	def iterateCollection(self, lst) -> typing.Any:
		return lst.members

	def isCollection(self, lst: typing.Any) -> bool:
		return hasattr(lst, "members")
		#return isinstance(lst.expr, (self.parserFactory.parsimonious.expressions.ZeroOrMore, self.parserFactory.parsimonious.expressions.OneOrMore))


class ParsimoniousVisitor(LiftingVisitor):
	__slots__ = ()

	@classmethod
	def Sequence(cls, l: Lifter, r, ctx):
		return cls._Seq(l, r, ctx)

	@classmethod
	def OneOf(cls, l: Lifter, ps, ctx):
		return cls._Alt(l, ps, ctx)

	@classmethod
	def ZeroOrMore(cls, l: Lifter, s, ctx):
		return cls.iter(0, s, ctx)

	@classmethod
	def OneOrMore(cls, l: Lifter, s, ctx):
		return cls.iter(1, s, ctx)

	@classmethod
	def Optional(cls, l: Lifter, s, ctx):
		return cls._Opt(l, s, ctx)

	@classmethod
	def Regex(cls, l: Lifter, s, ctx):
		return cls._regExp(l, s, ctx)

	@classmethod
	def Literal(cls, l: Lifter, r, ctx):
		return cls._literal(l, r, ctx)


class ParsimoniousLifter(Lifter):
	CONTEXT_TYPE = ParsimoniousLiftingContext
	VISITOR_TYPE = ParsimoniousVisitor
	AWALK = ParsimoniousParserBackendWalkStrategy(ParsimoniousParserFactory)

	def isToken(self, s, isCollection, ctx):
		return isinstance(s, ParsimoniousParserFactory.parsimonious.grammar.Literal)

	def getTokenText(self, node, ctx) -> str:
		return node.literal

	def getRegExpSource(self, node, ctx) -> str:
		return node.re.pattern

	@classmethod
	def getOriginalIdForAnElement(cls, s, ctx):
		return s.name

	@classmethod
	def setOriginalIdForAnElement(cls, s, ctx, v):
		s.name = v

	def parseToolSpecificGrammarIntoAST(self, grammarText, factory):
		return ParsimoniousParserFactory.parsimonious.Grammar(grammarText)

	def transformGrammar(self, ctx: LiftingContext):
		for id, s in ctx.pg.items():
			#print(id, s)
			self.convertAndInsertIntoNeededSection(s, ctx)


class Parsimonious(Tool):
	RUNNER = ParsimoniousRunner
	GENERATOR = ParsimoniousGenerator
	LIFTER = ParsimoniousLifter
