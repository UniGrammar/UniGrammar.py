import typing
from collections import OrderedDict
from enum import IntEnum

from ...core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, Name, Productions, Spacer, Tokens
from ...core.ast.base import Ref
from ...core.ast.characters import CharClass
from ...core.ast.tokens import Alt, Seq
from ..ast import Grammar
from .Runner import Runner


class InsertionAction:
	__slots__ = ("sect", "key")

	@property
	def element(self):
		return self.sect[self.key]

	def __init__(self, sect, key):
		self.sect = sect
		self.key = key

	def __repr__(self):
		return repr(self.sect) + "<-[" + repr(self.key) + "]"


class LiftingSection(OrderedDict):
	__slots__ = ("name", "ctx")

	def __init__(self, name: str, ctx: "LiftingContext"):
		self.name = name
		self.ctx = ctx

	@property
	def parentSect(self):
		return getattr(self.ctx.parent, self.name)

	def __getitem__(self, k):
		try:
			return super().__getitem__(k)
		except KeyError:
			if self.ctx.parent is not None:
				return self.parentSect[k]
			else:
				raise

	def setIndirect(self, k, v):
		#print(self.ctx.label, "setIndirect", k, v)
		insAct = InsertionAction(self, k)
		# Lifting a regexp like `a(aa)a` causes a failure on the second `a` because it is already present, as the first `a`
		assert k not in self, "Redefinition is not allowed. It loses the information. Key: " + repr(k) + "\tCurrent state: " + repr(self)
		super().__setitem__(k, v)
		assert self[k] is v
		self.ctx.insertionOrder.append(insAct)

		if self.ctx.parent:
			getattr(self.ctx.parent, self.name).setIndirect(k, v)

		return insAct

	def __setitem__(self, k, v):
		insAct = self.setIndirect(k, v)
		self.ctx.directInsertionOrder.append(insAct)

	def __len__(self):
		return super().__len__() + (len(self.parentSect) if self.ctx.parent else 0)


class UniqNameGenerator:
	__slots__ = ("prefix", "counter")

	def __init__(self, prefix):
		self.prefix = prefix
		self.counter = 0

	def __call__(self) -> str:
		res = self.prefix + "_" + str(self.counter)
		self.counter += 1
		return res


class LiftingContext:
	"""Stores the information needed for lifting"""

	sectsDicsNames = ("chars", "keywords", "fragmented", "tokens", "prods")
	__slots__ = sectsDicsNames + ("insertionOrder", "directInsertionOrder", "parent", "label", "anonNameGen", "pg", "grammar")
	SECTION_TYPE = LiftingSection

	def __init__(self, label=None):
		self.pg = None
		self.grammar = None
		self.parent = None
		self.insertionOrder = []
		self.directInsertionOrder = []
		self.label = label
		self.anonNameGen = UniqNameGenerator("anon")
		for nm in self.__class__.sectsDicsNames:
			setattr(self, nm, self.__class__.SECTION_TYPE(nm, self))

	def spawn(self, label=None):
		"""Create a child context from the current one"""
		newCtx = self.__class__(label)
		newCtx.pg = self.pg
		newCtx.grammar = self.grammar
		newCtx.parent = self
		return newCtx


class Lifter:
	"""A class, which instance is to be used for lifting"""

	__slots__ = ()

	RUNNER = None  # type: typing.Type[Runner] ,  initialized by Tool, don't set! manually

	CONTEXT_TYPE = LiftingContext  # type: typing.Type[LiftingContext]
	VISITOR_TYPE = None  # type: typing.Type[LiftingVisitor]
	AWALK = None  # type: ToolSpecificGrammarASTWalkStrategy
	TOOL_GENERATES_ASDAG = False  # Whether the tool native parser generates the AST  of the grammar DSL in the way that instead of reference AST nodes (nodes containing ids of other nodes) it generates python references (instead the actual node object is available there, and the AST is DAG)

	def convert(self, s, ctx: LiftingContext):
		processor = getattr(self.__class__.VISITOR_TYPE, s.__class__.__name__)
		return processor(self, s, ctx)

	def isKeyword(self, s, ctx: LiftingContext) -> bool:
		"""Returns whether the current AST node is a token, which is a character or a string that is verbatim hardcoded into the grammar"""
		raise NotImplementedError

	def getTokenText(self, node, ctx: LiftingContext) -> str:
		"""Must return the raw text of a token"""
		raise NotImplementedError

	def getRegExpSource(self, node, ctx: LiftingContext) -> str:
		"""Must return the text of the regular expression in the node."""
		raise NotImplementedError

	def getRegExpLifter(self, node, ctx: LiftingContext) -> typing.Any:
		"""Must return the class that can be used to lift the reg exp in the node. By default it is python reg exp, but if another kind is used, you can use it too."""
		from ...tools.regExps.python import PythonRegExpLifter

		return PythonRegExpLifter

	def getMatchingSection(self, r, ctx: LiftingContext) -> "Section":
		"""Must return the section into which the node will be inserted"""

		print("getMatchingSection", r)
		isCollection = self.AWALK.isCollection(r)
		if isCollection:
			isKeyword = False
			l = len(self.AWALK.iterateChildren(r))
		else:
			isKeyword = self.isKeyword(r, ctx)

		if isKeyword:
			l = len(self.getTokenText(r, ctx))
			if l != 1:
				return ctx.grammar.keywords
			else:
				return ctx.grammar.chars
		else:
			isToken = self.isToken(r, isCollection, ctx)
			if isToken:
				return ctx.grammar.tokens
			else:
				#isCharClass = self.isCharClass(r, ctx)
				return ctx.grammar.chars

		return ctx.grammar.prods

	@classmethod
	def getOriginalIdForAnElement(cls, s, ctx: LiftingContext) -> str:
		"""Returns id/name of target-specific AST node"""
		raise NotImplementedError

	@classmethod
	def setOriginalIdForAnElement(cls, s, ctx, v) -> None:
		"""Sets id/name into target-specific AST node. Though it becomes non-original, it then must be processed as if it was original."""
		raise NotImplementedError

	@classmethod
	def insertIntoSection(cls, node, section, iD, ctx: LiftingContext):
		section.children.append(Name(iD, node))

	def convertAndInsertIntoSection(self, node, section, ctx: LiftingContext):
		converted = self.convert(node, ctx)
		self.__class__.insertIntoSection(converted, section, self.__class__.getOriginalIdForAnElement(node, ctx), ctx)

	def convertAndInsertIntoNeededSection(self, node, ctx: LiftingContext):
		section = self.getMatchingSection(node, ctx)
		print("convertAndInsertIntoNeededSection section", section)
		self.convertAndInsertIntoSection(node, section, ctx)

	def makeRefAndInsertIfNeeded(self, s, ctx: LiftingContext, force: bool = None):
		if force is None:
			force = self.__class__.TOOL_GENERATES_ASDAG

		name = self.__class__.getOriginalIdForAnElement(s, ctx)
		shouldAssignNewName = not name
		if shouldAssignNewName:
			name = ctx.anonNameGen()
			self.__class__.setOriginalIdForAnElement(s, ctx, name)
		if force or shouldAssignNewName:
			self.convertAndInsertIntoNeededSection(s, ctx)
		return Ref(name)

	def genMetaTitle(self, ctx: LiftingContext) -> str:
		return "Generated from a " + self.__class__.RUNNER.PARSER.META.product.name + " grammar"

	def genMetaDoc(self, ctx: LiftingContext) -> str:
		return "This unigrammar was lifted from a " + self.__class__.RUNNER.PARSER.META.product.name + " grammar."

	def initGrammar(self, ctx: LiftingContext):
		ctx.grammar = Grammar(meta=GrammarMeta(iD=None, title=self.genMetaTitle(ctx), licence=None, doc=self.genMetaDoc(ctx), docRef=None, filenameRegExp=None), chars=Characters([]), keywords=Keywords([]), fragmented=Fragmented([]), tokens=Tokens([]), prods=Productions([]))

	def constructParserFactory(self) -> "UniGrammarRuntimeCore.IParser.IParserFactory":
		return self.__class__.RUNNER.PARSER()

	def parseToolSpecificGrammarIntoAST(self, grammarText: str, factory):
		raise NotImplementedError

	def transformGrammar(self, ctx: LiftingContext):
		raise NotImplementedError

	def __call__(self, grammarText: str) -> Grammar:
		ctx = self.__class__.CONTEXT_TYPE("root")
		fac = self.constructParserFactory()
		ctx.pg = self.parseToolSpecificGrammarIntoAST(grammarText, fac)
		self.initGrammar(ctx)
		self.transformGrammar(ctx)
		return ctx.grammar


class LiftingVisitor:
	"""Contains some methods to be called for nodes."""

	__slots__ = ()

	@classmethod
	def _Seq(cls, l: Lifter, r, ctx: LiftingContext):
		seqItems = []
		isKeyword = True
		for s in l.AWALK.iterateCollection(r):
			isKeyword &= l.isKeyword(s, ctx)
			seqItems.append(l.makeRefAndInsertIfNeeded(s, ctx))

		return Seq(*seqItems)

	@classmethod
	def _Opt(cls, l: Lifter, s, ctx: LiftingContext):
		return Opt(l.makeRefAndInsertIfNeeded(next(iter(l.AWALK.iterateCollection(s))), ctx))

	@classmethod
	def _Alt(cls, l: Lifter, ps, ctx: LiftingContext):
		alts = []
		for p in l.AWALK.iterateCollection(ps):
			alts.append(l.makeRefAndInsertIfNeeded(p, ctx))
		return Alt(*alts)

	@classmethod
	def iter(cls, l: Lifter, minCount, s, ctx: LiftingContext):
		return Iter(l.makeRefAndInsertIfNeeded(next(iter(l.AWALK.iterateCollection(s))), ctx), minCount)

	@classmethod
	def _literal(cls, l: Lifter, r, ctx: LiftingContext):
		s = l.getMatchingSection(r, ctx)
		return CharClass(l.getTokenText(r, ctx), False)

	@classmethod
	def _regExp(cls, l: Lifter, s, ctx: LiftingContext):
		p = l.getRegExpSource(s, ctx)
		rLCtor = l.getRegExpLifter(s, ctx)
		print("Regex pattern: ", p)
		rL = rLCtor()
		print("Regex lifter: ", rL)
		rxGrammar = rL(p)
		ctx.grammar.embed(rxGrammar)
		return None


class LifterCommand:
	__slots__ = ()


class insertIntoSection(LifterCommand):
	__slots__ = ("node", "section", "id")

	def __init__(self):
		self.node = node
		self.section = section
		self.id = iD
