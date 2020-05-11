import typing
from pathlib import Path
from warnings import warn

from UniGrammarRuntime.backends.python.parglare import ParglareParserFactory, toolGitRepo
from UniGrammarRuntime.DSLMetadata import DSLMetadata
from UniGrammarRuntime.grammarClasses import GLR, LR
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources
from UniGrammarRuntime.ToolMetadata import Product, ToolMetadata
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ...core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, Name, Productions, Spacer, Tokens
from ...core.ast.base import Group, Name, Ref
from ...core.ast.characters import CharClass, CharClassUnion
from ...core.ast.prods import Prefer
from ...core.ast.tokens import Alt, Opt, Seq
from ...core.backend.Generator import Generator, GeneratorContext, TranspiledResult
from ...core.backend.Lifter import Lifter, LiftingContext, LiftingVisitor
from ...core.backend.Runner import Runner
from ...core.backend.SectionedGenerator import Sectioner
from ...core.backend.Tool import Tool
from ...generators.pythonicGenerator import PythonicGenerator


class ParglareRunner(Runner):
	__slots__ = ()

	COMPILER = DummyCompiler
	PARSER = ParglareParserFactory

	def compileAndSave(self, internalRepr, grammarResources: InMemoryGrammarResources, meta: ToolMetadata, target: str = "python"):
		super().compileAndSave(internalRepr, grammarResources, meta, target)
		"""TODO: create .pgt file
		from parglare.tables.persist import table_from_serializable, table_to_serializable
		p = parglare.grammar.get_grammar_parser(False, False)
		p.parse(grammarText.read_text())
		p.table
		"""

	def execute(self, g: typing.Any) -> typing.Any:
		return g

	def parse(self, parser: "parglare.parser.Parser", text: str) -> None:
		parser.parse(text)

	def trace(self, parser: "parglare.parser.Parser", text: str):
		raise NotImplementedError()
		#grammar_pda_export(table, "%s.dot" % gF)

	def visualize(self, parser: "parglare.parser.Parser", text: str):
		raise NotImplementedError()


class ParglareGenerator(PythonicGenerator):
	META = ParglareParserFactory.FORMAT

	assignmentOperator = ": "
	capturingOperator = "="
	endStatementOperator = ";"
	singleLineCommentStart = "//"
	emptyTerminalConstant = "EMPTY"

	CONTEXT_CLASS = GeneratorContext

	DEFAULT_ORDER = ("prods", "fragmented", "LAYOUT", "keywords", "tokens", "terminalsKeyword", "chars")

	class SECTIONER(Sectioner):
		@classmethod
		def LAYOUT(cls, backend: Generator, gr: Grammar, ctx: typing.Any = None):
			yield "LAYOUT: EMPTY;"

		@classmethod
		def terminalsKeyword(cls, backend: Generator, gr: Grammar, ctx: typing.Any = None):
			yield "terminals"

	@classmethod
	def Opt(cls, obj, grammar: Grammar, ctx: typing.Any = None) -> str:
		"""see https://github.com/igordejanovic/parglare/issues/144
		Also we need the SEPARATE rules for name_opt: name | EMPTY; because otherwise our postprocessing fails. It means for example if we createe a rule
		b: a?;
		then parglare will implicitly desugar it into
		b: a_opt;
		a_opt: a | EMPTY;

		and we need BOTH of them, because only in this case the structure of AST matches the structures generated by other tools.
		"""

		if ctx.currentProdName.endswith("_opt"):
			raise ValueError("Don't call your productions like that! Parglare uses this to desugar the names.", ctx.currentProdName)

		requiresWorkaround = len(ctx.stack) > 1 and isinstance(ctx.stack[-2], Prefer)

		if requiresWorkaround:
			ctx.stack.pop()  # replacing with Alt
			sugaredProdName = ctx.currentProdName
			desugarProdName = sugaredProdName + "_opt"

			cls.resolve(Name(desugarProdName, Alt(obj.child, cls.emptyTerminalConstant)), grammar, ctx)

			# returning to its place
			ctx.stack.append(obj)

			return cls.resolve(Ref(desugarProdName), grammar, ctx)

		return super().Opt(obj, grammar, ctx)

	#@classmethod
	#def Prefer(cls, obj: Prefer, grammar: Grammar, ctx: typing.Any = None) -> str:
	#	if isinstance(obj.child, Opt):
	#
	#
	#	return cls._Prefer(cls.resolve(obj.child, grammar, ctx), obj.preference, grammar)

	@classmethod
	def _Prefer(cls, res: str, preference: str, grammar: Grammar) -> str:
		return cls._Seq([res, "{" + preference + "}"], grammar)


class ParglareLiftingContext(LiftingContext):
	__slots__ = ("pg", "grammar")

	def __init__(self, label=None):
		super().__init__(label)
		self.pg = None
		self.grammar = None

	def spawn(self, label=None):
		res = super().spawn(label)
		res.pg = self.pg
		res.grammar = self.grammar
		return res


class ParglareVisitor(LiftingVisitor):
	__slots__ = ()

	@classmethod
	def processSeq(cls, r, ctx=None):
		seqItems = []
		isToken = True
		for s in r.members:
			isToken &= isinstance(s, ParglareParserFactory.parglare.grammar.Terminal)
			seqItems.append(Ref(s.fqn))
		return Seq(*seqItems), (ctx.grammar.tokens if isToken else ctx.grammar.prods)

	@classmethod
	def processAlt(cls, ps, ctx=None):
		alts = []
		for p in ps:
			if len(p.rhs) > 1:
				raise ValueError("This production is incomaptible to Alt. Move Seq into a separate production.")
			elif len(p.rhs) < 1:
				raise ValueError("Empty production")
			alts.append(p.rhs[0])
		return Alt(*alts), ctx.grammar.prods

	@classmethod
	def processNonTerminal(cls, s, ctx=None):
		#s.fqn
		#s.name
		#if len(s.productions) == 1:
		#	return cls.processSeq(s.productions[0], ctx), ctx.grammar.prods
		#else:
		return cls.processAlt(s.productions, ctx), ctx.grammar.prods

	@classmethod
	def processTerminal(cls, r, ctx=None):
		# raise ValueError("Unknown parglare AST terminal node", s)
		if isinstance(r, ParglareParserFactory.parglare.grammar.StringRecognizer):
			if r.ignore_case:
				raise ValueError("UniGrammar doesn't support caseless matching yet")
			print(r.value, r.ignore_case)

			if len(r.value) == 1:
				sect = ctx.grammar.keywords
			else:
				sect = ctx.grammar.chars
			return CharClass(r.value, False), sect
		else:
			raise ValueError("Unknown parglare AST terminal node recognizer", r)

	@classmethod
	def resolve(cls, s, ctx=None):
		#s.prior
		#s.prefer
		if isinstance(s, ParglareParserFactory.parglare.grammar.NonTerminal):
			return cls.processNonTerminal(s, ctx)
		elif isinstance(s, ParglareParserFactory.parglare.grammar.Terminal):
			return cls.processTerminal(s.recognizer, ctx)
		elif isinstance(s, ParglareParserFactory.parglare.grammar.RegExRecognizer):
			raise NotImplementedError("RegExRecognizer not yet implemented", dir(s), s.__class__.__mro__)
		else:
			raise ValueError("Unknown parglare AST node", s, s.__class__.__mro__)


class ParglareLifter(Lifter):
	CONTEXT_TYPE = ParglareLiftingContext

	def __call__(self, grammarText: str):
		ctx = self.__class__.CONTEXT_TYPE("root")
		ctx.grammar = Grammar(meta=GrammarMeta(iD=None, title="Generated from a parglare grammar", licence=None, doc="This grammar was transpiled from a parglare grammar.", docRef=None, filenameRegExp=None), chars=Characters([]), keywords=Keywords([]), fragmented=Fragmented([]), tokens=Tokens([]), prods=Productions([]))
		(ParglareParserFactory())
		ctx.pg = ParglareParserFactory.parglare.Grammar.from_string(grammarText)

		for id, s in ctx.pg.symbols_by_name.items():
			#print(id, s)
			res, sect = ParglareVisitor.resolve(s, ctx)
			if res:
				sect.children.append(res)

		return grammar


class Parglare(Tool):
	RUNNER = ParglareRunner
	GENERATOR = ParglareGenerator
	LIFTER = ParglareLifter