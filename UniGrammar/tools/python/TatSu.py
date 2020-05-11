import typing
from pathlib import Path

from UniGrammarRuntime.backends.python.TatSu import TatSuParserFactory, TatSuParserFactoryFromSource, toolGitRepo
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import PEG
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata

from ...core.ast import Grammar, Spacer
from ...core.backend.Generator import TranspiledResult
from ...core.backend.Lifter import Lifter, LiftingContext, LiftingVisitor
from ...core.backend.Runner import Runner
from ...core.backend.SectionedGenerator import Sectioner
from ...core.backend.Tool import Tool
from ...generators.pythonicGenerator import PythonicGenerator


class TatSuRunner(Runner):
	__slots__ = ()

	COMPILER = TatSuParserFactoryFromSource
	PARSER = TatSuParserFactory

	def trace(self, parser, text: str):
		raise NotImplementedError("Not yet implemented")

	def visualize(self, parser, text: str):
		raise NotImplementedError()

	def saveCompiled(self, internalRepr, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target: str = "python"):
		import tatsu

		grammarResources.parent.backendsTextData[meta.product.name, grammarResources.name + "." + "py"] = tatsu.codegen.codegen(internalRepr, target=target)
		#grammarResources.parent.backendsTextData[meta.name, grammarResources.name + "." + meta.mainExtension] = internalRepr

	def compileAndSave(self, transpiledResult: TranspiledResult, grammarResources: InMemoryGrammarResources, target: typing.Optional[str] = "python") -> None:
		import tatsu


class TatSuGenerator(PythonicGenerator):
	META = TatSuParserFactoryFromSource.FORMAT

	assignmentOperator = " = "
	capturingOperator = ":"
	endStatementOperator = ";"
	singleLineCommentStart = "#"
	DEFAULT_ORDER = ("prods", "fragmented", "keywords", "chars", "tokens")

	class SECTIONER(Sectioner):
		@classmethod
		def START(cls, backend: PythonicGenerator, gr: Grammar, ctx: typing.Any = None):
			yield from super(cls, cls).START(backend, gr)
			yield "@@grammar :: " + gr.meta.id
			yield "@@whitespace :: //"
			yield "@@left_recursion :: False"
			yield backend.resolve(Spacer(2), gr, ctx)

	@classmethod
	def wrapZeroOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "{" + res + "}*"

	@classmethod
	def wrapOneOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "{" + res + "}+"

	@classmethod
	def wrapZeroOrOne(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "[" + res + "]"


class TatSuLiftingContext(LiftingContext):
	__slots__ = ("tg", "grammar")

	def __init__(self, label=None):
		super().__init__(label)
		self.tg = None
		self.grammar = None

	def spawn(self, label=None):
		res = super().spawn(label)
		res.tg = self.tg
		res.grammar = self.grammar
		return res


class TatSuVisitor(LiftingVisitor):
	__slots__ = ()

	@classmethod
	def NegativeLookahead(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def EmptyClosure(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def EOLComment(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def SkipTo(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Join(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Fail(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def BasedRule(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Special(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def RuleInclude(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def OverrideList(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def LeftJoin(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Constant(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Gather(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Lookahead(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def PositiveGather(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Comment(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Void(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def RightJoin(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Any(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def PositiveJoin(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def PositiveClosure(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Model(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def NamedList(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Decorator(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def EOF(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Override(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Cut(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def Named(cls, s, ctx=None):
		raise NotImplementedError

	@classmethod
	def convert(cls, s, ctx=None):
		#s.prior
		#s.prefer
		if isinstance(s, TatSuParserFactory.tatsu.grammar.NonTerminal):
			return cls.processNonTerminal(s, ctx)
		elif isinstance(s, TatSuParserFactory.tatsu.grammar.Terminal):
			return cls.processTerminal(s.recognizer, ctx)
		elif isinstance(s, TatSuParserFactory.tatsu.grammar.RegExRecognizer):
			raise NotImplementedError("RegExRecognizer not yet implemented", dir(s), s.__class__.__mro__)
		else:
			raise ValueError("Unknown tatsu AST node", s, s.__class__.__mro__)

	@classmethod
	def convertContainer(cls, s, ctx=None):
		processedChildren = []
		for r in ctx.tg.children():
			processedChildren.push(cls.convert(s, ctx))
		return processedChildren

	@classmethod
	def Pattern(cls, s, ctx=None):
		raise NotImplementedError()
		s.regex.pattern

	@classmethod
	def Rule(cls, s, ctx=None):
		return Name(s.name, s.children[0])

	@classmethod
	def Token(cls, s, ctx=None):
		if len(r.value) == 1:
			return Lit(t.token), ctx.grammar.keywords
		else:
			return CharClass(t.token, False), ctx.grammar.chars

	@classmethod
	def Sequence(cls, s, ctx=None):
		return Seq(cls.processedChildren(s))

	@classmethod
	def Optional(cls, s, ctx=None):
		return Opt(s.children()[0])

	@classmethod
	def RuleRef(cls, s, ctx=None):
		return Ref(r.name)

	@classmethod
	def Group(cls, s, ctx=None):
		return Iter(s.children()[0], 1)

	@classmethod
	def Closure(cls, s, ctx=None):
		return Iter(s.children()[0], 0)

	@classmethod
	def Choice(cls, s, ctx=None):
		return Alt(c.children())

	@classmethod
	def Grammar(cls, s, ctx=None):
		processedChildren = cls.convertContainer(s, ctx)
		for res, sect in processedChildren:
			if res:
				sect.children.append(res)


class TatSuLifter(Lifter):
	CONTEXT_TYPE = TatSuLiftingContext

	def parseToolSpecificGrammarIntoAST(self, grammarText, factory):
		return TatSuParserFactory.tatsu.compile(grammarText)

	def transformGrammar(self, ctx: LiftingContext):
		TatSuVisitor(ctx.tg)


class TatSu(Tool):
	RUNNER = TatSuRunner
	GENERATOR = TatSuGenerator
