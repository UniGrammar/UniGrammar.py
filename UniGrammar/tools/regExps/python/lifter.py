import sre_constants as sc
import typing
import unicodedata
import warnings
from pprint import pprint

from UniGrammarRuntime.IParsingBackend import ToolSpecificGrammarASTWalkStrategy

from ....core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, MultiLineComment, Name, Productions, Spacer, Tokens
from ....core.ast.base import Node, Ref
from ....core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ....core.ast.prods import Cap, Prefer
from ....core.ast.tokens import Alt, Iter, Lit, Opt, Seq
from ....core.backend.Lifter import Lifter, LiftingContext, LiftingVisitor
from .knowledge import LITERAL_STR, anyChar, wellKnownRegExpRemap
from .prelifter import *


class PyREVisitor(LiftingVisitor):
	@classmethod
	def LITERAL(cls, l: Lifter, node: typing.Tuple[int], ctx=None):
		return CharClass(node.literal)

	@classmethod
	def ANY(cls, l: Lifter, reserved):
		ctx.chars["ANY"] = anyChar

	@classmethod
	def IN(cls, l: Lifter, node, ctx=None):
		cc = CharClass([])
		children = []
		negative = False
		loneChildName = None
		for cc in node.children:
			print(cc)
			if cc.type == sc.NEGATE:
				negative = True
			elif cc.type in {sc.LITERAL, LITERAL_STR}:
				cc.chars.append(cs.literal)
				loneChildName = unicodedata.name(c).replace(" ", "_").upper()
			elif cc.type == sc.CATEGORY:
				children.append(wellKnownRegExpRemap[cc.enumV])
				loneChildName = "CHARS_" + cc.enumV.name[9:]
			elif cc.type == sc.RANGE:
				children.append(CharRange.fromBounds(start=chr(cc.start), stop=chr(cc.stop)))
				loneChildName = "CHARS_RANGE_" + str(cc.start) + "_" + str(cc.stop)
		if len(children) == 1:
			loneChild = children[0]
			loneChild.negative = negative
			if loneChildName is not None:
				name = loneChildName
			else:
				name = "CHARS_" + cc.type.name + "_" + str(len(ctx.chars))
			return loneChild
		else:
			return CharClassUnion(children, negative=negative)

	@classmethod
	def GROUPREF(cls, l: Lifter, node, ctx=None):
		raise ValueError("backrefs are completely not supported!")

	@classmethod
	def AT(cls, l: Lifter, node, ctx=None):
		warnings.warn("AT opcode is ignored " + repr(where))
		# AT_BEGINNING_STRING \\A
		# AT_END_STRING \\Z

	def ASSERT_NOT(relativePosition, subSeq, ctx=None):
		raise ValueError("negative conditions are completely not supported!")

	@classmethod
	def MIN_REPEAT(cls, l: Lifter, node, ctx=None):
		"""Non-greedy matching"""
		warnings.warn("Non-greedy matching is not yet implemented, replacing with greedy one")
		return cls.MAX_REPEAT(l, node, ctx=ctx)

	@classmethod
	def SUBPATTERN(cls, l: Lifter, node, ctx=None):
		return cls._Seq(l, node, ctx)

	@classmethod
	def CAPTURE_GROUP(cls, l: Lifter, node, ctx=None):
		child = node.children[0]
		print(child)
		return Cap(node.name, l.convert(child, ctx))

	@classmethod
	def MAX_REPEAT(cls, l: Lifter, node, ctx=None):
		assert len(node.children) == 1, "Strange iterArgs, IRL it is always of len 1: " + repr(node.children)
		child = node.children[0]

		subExprRef = l.makeRefAndInsertIfNeeded(child, ctx)

		print("maxCount", node.maxCount, node.maxCount != sc.MAXREPEAT)  # MAXREPEAT (without underscore) is for repeating indefinitely, MAX_REPEAT (with underscore) is opcode

		if node.maxCount == sc.MAXREPEAT:
			node.maxCount = None

		childName = subExprRef.name + "_iter"
		newCtx = ctx.spawn(childName)

		if node.minCount == 0 and node.maxCount == 1:
			return Opt(subExprRef)
		else:
			return Iter(subExprRef, node.minCount, node.maxCount)

	@classmethod
	def BRANCH(cls, l: Lifter, node, ctx=None):
		return cls._Alt(l, node, ctx)


class REConvertingContext(LiftingContext):
	__slots__ = ("prevStr",)

	def __init__(self, label=None):
		super().__init__(label)
		self.prevStr = []


class PythonRegExpLifterWalkStrategy(ToolSpecificGrammarASTWalkStrategy):
	__slots__ = ()

	def iterateChildren(self, node):
		return node.children

	def isTerminal(self, node):
		raise NotImplementedError

	def iterateCollection(self, lst) -> typing.Any:
		return lst.children

	def isCollection(self, lst) -> bool:
		return hasattr(lst, "children")


class PythonRegExpLifter(Lifter):
	CONTEXT_TYPE = REConvertingContext
	AWALK = PythonRegExpLifterWalkStrategy(None)
	VISITOR_TYPE = PyREVisitor
	TOOL_GENERATES_ASDAG = True

	####################

	def getTokenText(self, node, ctx) -> str:
		return node.literal

	@classmethod
	def getOriginalIdForAnElement(cls, s, ctx):
		return s.name

	@classmethod
	def setOriginalIdForAnElement(cls, s, ctx, v):
		s.name = v

	###################

	def convert(self, s, ctx: LiftingContext):
		processor = getattr(self.__class__.VISITOR_TYPE, s.type.name)
		return processor(self, s, ctx)

	def isToken(self, node, isCollection, ctx: LiftingContext) -> bool:
		return node.type in {sc.LITERAL, LITERAL_STR}

	def getRegExpLifter(self, node, ctx: LiftingContext) -> typing.Any:
		raise NotImplementedError("This is a regexp itself, this method must never be called for this lifter")

	###################

	def parseToolSpecificGrammarIntoAST(self, grammarText: str, factory):
		return PythonRXAST(grammarText)

	def transformGrammar(self, ctx: LiftingContext):
		ctx.pg.root.name = ctx.grammar.meta.id
		self.convertAndInsertIntoNeededSection(ctx.pg.root, ctx)
		print("transformGrammar", ctx.grammar)

	def genMetaTitle(self, ctx: LiftingContext) -> str:
		return "Generated from the Python regexp `" + ctx.pg.pattern.str + "`"

	def genMetaDoc(self, ctx: LiftingContext) -> str:
		return "This grammar was converted from the Python regexp `" + ctx.pg.pattern.str + "`"
