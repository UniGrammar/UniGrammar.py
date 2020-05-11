import typing
from abc import ABCMeta, abstractmethod
from collections import deque

from escapelib import defaultCharClassEscaper, defaultStringEscaper

from ..ast import Characters, Comment, Embed, Fragmented, Grammar, Import, Keywords, MultiLineComment, Productions, Spacer, Tokens
from ..ast.base import Group, Node
from ..ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ..ast.prods import Cap, Prefer, UnCap
from ..ast.templates import TemplateInstantiation
from ..ast.tokens import Alt, Iter, Lit, Opt, Seq
from ..CodeGen import CodeGen, CodeGenContext
from ..defaults import ourProjectLink
from ..templater import expandTemplates


class TranspiledResult:
	__slots__ = ("id", "text")

	def __init__(self, iD: str, text: str = None, tests: None = None) -> None:
		self.id = iD
		self.text = text

	def __str__(self):
		return self.text

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.id) + ", " + repr(self.text) + ")"


class GeneratorContext(CodeGenContext):
	__slots__ = ("stack", "section")

	def __init__(self, currentProdName: typing.Optional[str]) -> None:
		self.stack = deque(())
		self.sectionNode = None
		super().__init__(currentProdName)


class Generator(CodeGen):
	__slots__ = ()
	META = None
	charClassEscaper = defaultCharClassEscaper
	stringEscaper = defaultStringEscaper
	CONTEXT_CLASS = GeneratorContext

	GROUP_WRAPPERS = ("(", ")")

	@classmethod
	def getGreeting(cls, obj: Grammar) -> typing.Iterable[str]:
		if isinstance(cls.META.product.website, str):
			toolWebsiteStr = cls.META.product.website
		elif isinstance(cls.META.product.website, tuple):
			toolWebsiteStr = ", ".join(cls.META.product.website)

		yield from (
			"Generated by UniGrammar (" + ourProjectLink + ")",
			"for " + cls.META.product.name + " (" + toolWebsiteStr + ") DSL",
		)
		yield ""

		if obj.meta.doc:
			for s in obj.meta.doc.split("\n"):
				s = s.strip()
				yield s
		yield ""

		if obj.meta.docRef:
			yield "References:"
			dr = obj.meta.docRef
			if isinstance(dr, str):
				dr = (dr,)
			for s in dr:
				yield "\t" + s.strip()

		if obj.meta.filenameRegExp:
			yield "Use with files which names are matching the regexp: " + obj.meta.filenameRegExp

	@classmethod
	def getHeader(cls, obj: Grammar) -> typing.Iterable[str]:
		yield cls.resolve(MultiLineComment(greetingLine for greetingLine in cls.getGreeting(obj)), obj)
		yield cls.resolve(Spacer(2), obj)

	@classmethod
	def Section(cls, arr: typing.Any, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		ctx.sectionNode = arr
		for obj in arr.children:
			res = cls.resolve(obj, grammar, ctx)
			yield res

	@classmethod
	@abstractmethod
	def _Name(cls, k: str, v: str, ctx: typing.Any = None) -> str:
		raise NotImplementedError

	@classmethod
	def _emplaceRule(cls, k: str, v: str, ctx: typing.Any = None) -> str:
		"""As a fallback we immediately generate rule source code. Though usually we need a layer of indirection to allow adding rules while processing other rules"""
		return cls._Name(k, v, ctx)

	@classmethod
	def Name(cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx: typing.Any = None) -> str:
		nm = obj.name
		expr = obj.child
		section = ctx.sectionNode
		ctx = ctx.spawn()
		ctx.currentProdName = nm
		ctx.sectionNode = section
		result = cls.resolve(expr, grammar, ctx)
		return cls._emplaceRule(ctx.currentProdName, result, ctx)  # To allow renaming current rule

	@classmethod
	def resolve(cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx: typing.Any = None, allowWrappingIntoAGroup: bool = True) -> str:
		if isinstance(obj, str):
			return obj

		if not isinstance(obj, Node):
			raise ValueError("This stuff must be a Node", obj)

		if ctx:
			ctx.stack.append(obj)

		if allowWrappingIntoAGroup:
			obj = cls._wrapIntoGroupIfNeeded(obj, grammar, ctx, debug=None)

		if ctx:
			ctx.stack.pop()

		objCls = type(obj)
		clsNm = objCls.__name__
		processor = getattr(cls, clsNm)

		# ToDo: split into a separate methods, one having nothing to do with ctx and another one using it
		if ctx:
			if not objCls.STACK_INVISIBLE:
				ctx.stack.append(obj)

		res = processor(obj, grammar, ctx)
		if ctx:
			if not objCls.STACK_INVISIBLE:
				ctx.stack.pop()
		return res

	@classmethod
	def _hasPrefer(cls) -> bool:
		"""checking if the grammar has Prefer nodes, just cls._Prefer is __class__._Prefer doesn't work"""
		return cls._Prefer.__code__ is not __class__._Prefer.__code__

	# Dealing with auto-grouping
	@classmethod
	def _shouldWrapIntoAGroup(cls, obj, grammar: Grammar, ctx: typing.Any = None, debug: typing.Optional[bool] = None) -> typing.Tuple[bool, typing.Iterable[str]]:
		if ctx and len(ctx.stack) > 1:
			debugOut = ()
			if debug is not None:
				import inspect

				debugOut = [repr(ctx.stack)]

			parent = ctx.stack[-2]
			this = ctx.stack[-1]

			conditions = (
				(lambda: isinstance(this, Iter) and isinstance(parent, Iter), True),
				(lambda: this.__class__ == parent.__class__, False),  # will be merged
				(lambda: isinstance(this, Prefer), cls._hasPrefer()),
				(lambda: isinstance(this, (Seq, Alt)), not isinstance(parent, Prefer)),
				(lambda: isinstance(this, Cap) and isinstance(parent, Iter), True),
			)

			for pred, res in conditions:
				matches = pred()
				if debug is not None:
					src = inspect.getsource(pred)
					debugOut.append(src.strip() + " ? " + repr(matches))

				if matches:
					if debug is not None:
						debugOut[-1] += " -> " + repr(res)
					return res, debugOut

			return False, debugOut

		return False, ()

	@classmethod
	def _wrapIntoGroupIfNeeded(cls, obj, grammar: Grammar, ctx: typing.Any = None, debug: typing.Optional[bool] = None):
		should, debugOut = cls._shouldWrapIntoAGroup(obj, grammar, ctx, debug=debug)

		if debug is not None:
			import sys

			if should == debug:
				for el in debugOut:
					print(el, file=sys.stderr)

		if should:
			res = Group(obj)
			if debug is not None:
				print("Wrapping into group:", res, file=sys.stderr)
			return res

		return obj

	@classmethod
	def _wrapIntoGroup(cls, s: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.GROUP_WRAPPERS[0] + s + cls.GROUP_WRAPPERS[1]

	@classmethod
	def Group(cls, obj: Group, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls._wrapIntoGroup(cls.resolve(obj.child, grammar, ctx, allowWrappingIntoAGroup=False), grammar, ctx)

	########

	@classmethod
	def Characters(cls, obj: Characters, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls.Section(obj, grammar, ctx)

	@classmethod
	def Keywords(cls, obj: Keywords, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls.Section(obj, grammar, ctx)

	@classmethod
	def Tokens(cls, obj: Tokens, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls.Section(obj, grammar, ctx)

	@classmethod
	def Productions(cls, obj: Productions, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls.Section(obj, grammar, ctx)

	@classmethod
	def Fragmented(cls, obj: Fragmented, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterator[str]:
		return cls.Section(obj, grammar, ctx)

	@classmethod
	def Seq(cls, obj: Seq, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls._Seq(obj.children, grammar, ctx)

	@classmethod
	def _Seq(cls, arr: typing.Iterable[Node], grammar: Grammar, ctx: typing.Any = None) -> str:
		return " ".join(cls.resolve(c, grammar, ctx) for c in arr)

	@classmethod
	def Lit(cls, obj: Lit, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.wrapLiteralString(obj.value)

	@classmethod
	def wrapLiteralString(cls, s: str) -> str:
		return '"' + cls.stringEscaper(s) + '"'

	@classmethod
	def wrapLiteralChar(cls, s: str) -> str:
		wrapped = cls.wrapLiteralString(s)
		return wrapped

	@classmethod
	def Iter(cls, obj: Iter, grammar: Grammar, ctx: typing.Any = None) -> str:
		ch = cls.resolve(obj.child, grammar, ctx)
		minCount = obj.minCount
		# pylint: disable=no-else-return
		if minCount == 0:
			return cls.wrapZeroOrMore(ch, grammar)
		elif minCount == 1:
			return cls.wrapOneOrMore(ch, grammar)
		return cls.wrapNOrMore(minCount, ch, grammar)

	@classmethod
	@abstractmethod
	def wrapZeroOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def wrapZeroOrOne(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def wrapOneOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError()

	@classmethod
	def wrapNOrMore(cls, minCount: int, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls._Seq([res] * minCount + [cls.wrapZeroOrMore(res, grammar)], grammar)

	@classmethod
	def Opt(cls, obj: Opt, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.wrapZeroOrOne(cls.resolve(obj.child, None, ctx), grammar, ctx)

	@classmethod
	@abstractmethod
	def _Cap(cls, k: str, v: str) -> str:
		raise NotImplementedError

	@classmethod
	def Cap(cls, obj: Cap, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
		return cls._Cap(obj.name, cls.resolve(obj.child, grammar, ctx))

	@classmethod
	def Prefer(cls, obj: Prefer, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls._Prefer(cls.resolve(obj.child, grammar, ctx), obj.preference, grammar)

	@classmethod
	def _Prefer(cls, res: str, preference: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return res

	@classmethod
	def Spacer(cls, obj: Spacer, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "\n" * (obj.count - 1)  # we join lines, so an empty line without \n counts

	@classmethod
	def UnCap(cls, obj: UnCap, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.resolve(obj.child, grammar, ctx)

	############

	@classmethod
	@abstractmethod
	def _Comment(cls, comment: str) -> str:
		raise NotImplementedError

	@classmethod
	def Comment(cls, obj: Comment, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls._Comment(obj.value)

	@classmethod
	def MultiLineComment(cls, obj: MultiLineComment, grammar: Grammar, ctx: typing.Any = None) -> str:
		return "\n".join((cls._Comment(line) if line else "") for line in obj.value)

	@classmethod
	@abstractmethod
	def CharClass(cls, obj: CharClass, grammar: Grammar):
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def WellKnownChars(cls, obj: WellKnownChars, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError

	@classmethod
	@abstractmethod
	def CharClassUnion(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError

	@classmethod
	@abstractmethod
	def CharRange(cls, obj: CharRange, grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError

	@classmethod
	def Alt(cls, obj: Alt, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls._wrapAlts((cls.resolve(c, grammar, ctx) for c in obj.children), grammar)

	@classmethod
	@abstractmethod
	def _wrapAlts(cls, alts: typing.Iterable[str], grammar: Grammar, ctx: typing.Any = None) -> str:
		raise NotImplementedError()

	@classmethod
	def preprocessGrammar(cls, grammar: Grammar, ctx: typing.Any = None) -> None:
		expandTemplates(grammar, cls, ctx, grammar)

	@classmethod
	def TemplateInstantiation(cls, obj: TemplateInstantiation, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise Exception("There must be no templates when we are generating code. They must be already expanded")

	@classmethod
	@abstractmethod
	def embedGrammar(cls, obj: Grammar, ctx: typing.Any = None) -> typing.Any:
		"""Embeds content of a grammar into current transpiled document. Used when creating a new document too."""
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def _Import(cls, obj: Embed, embedIntermediateRepr: typing.Any, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	def Import(cls, obj: Import, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()
		#return cls.embedGrammar(g, ctx)

	@classmethod
	def initContext(cls, grammar):
		return cls.CONTEXT_CLASS(None)

	@classmethod
	@abstractmethod
	def _transpile(cls, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
		"""A function generating lines of the source. Redefine it in subclasses."""
		raise NotImplementedError()