import sre_constants as sc
import sre_parse as sp
import typing

from UniGrammarRuntime.backends.regExps.python import PythonRegExpParserFactory, toolGitRepo
from UniGrammarRuntime.IParsingBackend import ToolSpecificGrammarASTWalkStrategy

from ....core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, MultiLineComment, Name, Productions, Spacer, Tokens
from ....core.ast.base import Node, Ref
from ....core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ....core.ast.prods import Cap, Prefer
from ....core.ast.tokens import Alt, Iter, Lit, Opt, Seq
from ....core.backend.Generator import Generator, GeneratorContext, TranspiledResult
from ....core.backend.Lifter import Lifter, LiftingContext, LiftingVisitor
from ....core.CharClassProcessor import CharClassProcessor, CharRangeProcessor
from ....generators.UniGrammarDictGenerator import UniGrammarDictGenerator
from .knowledge import anyChar, wellKnownRegExpInvRemapSingle


class PythonRegExpGeneratorContext(UniGrammarDictGenerator.CONTEXT_CLASS):
	__slots__ = ("sp", "refsPtrs")

	def __init__(self, currentProdName: typing.Optional[str]) -> None:
		state = sp.State()
		self.sp = sp.SubPattern(state)
		self.refsPtrs = {}
		super().__init__(currentProdName)


class PythonRegExpCharRangeProcessor(CharRangeProcessor):
	__slots__ = ()

	def __call__(self, classProcessor: "CharClassProcessor", backend: typing.Type[Generator], obj: CharRange, grammar: Grammar) -> str:
		return (RANGE, (obj.start, obj.end))


class PythonRegExpGenerator(UniGrammarDictGenerator):
	__slots__ = ()
	META = PythonRegExpParserFactory.FORMAT
	charClassEscaper = None
	stringEscaper = None
	CONTEXT_CLASS = PythonRegExpGeneratorContext

	class CHAR_CLASS_PROCESSOR(CharClassProcessor):
		@classmethod
		def union(cls, backend, union, grammar):
			raise NotImplementedError()

		@classmethod
		def encloseCharClass(cls, s: str, obj: CharClass, grammar: Grammar) -> str:
			return cls.s

		@classmethod
		def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			return (IN, [(NEGATE, None), s])

		@classmethod
		def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
			return s

		range = classmethod(PythonRegExpCharRangeProcessor())

	@classmethod
	def getHeader(cls, obj: Grammar):
		pass

	@classmethod
	def Section(cls, arr: typing.Any, grammar: Grammar, ctx: typing.Any = None):
		res = []
		for obj in arr.children:
			objRes = cls.resolve(obj, grammar, ctx)
			#ic(obj, objRes)
			res.append(objRes)
		return res

	@classmethod
	def Name(cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx: typing.Any = None) -> str:
		res = cls.resolve(obj.child, grammar, ctx)
		ctx.refsPtrs[obj.name] = res
		return res

	@classmethod
	def _Seq(cls, arr: typing.Iterable[Node], grammar: Grammar, ctx: typing.Any = None) -> str:
		return [cls.resolve(c, grammar, ctx) for c in arr]

	@classmethod
	def _char(cls, v: str) -> typing.Tuple:
		return (sc.LITERAL, ord(v))

	@classmethod
	def Lit(cls, obj: Lit, grammar: Grammar, ctx: typing.Any = None) -> str:
		v = obj.value
		if len(v) == 1:
			return cls._char(v)

		return [cls._char(c) for c in v]

	@classmethod
	def Iter(cls, obj: Iter, grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.MAX_REPEAT, (obj.minCount, sc.MAXREPEAT, [cls.resolve(obj.child, None, ctx)]))

	@classmethod
	def Opt(cls, obj: Opt, grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.MAX_REPEAT, (0, 1, [cls.resolve(obj.child, None, ctx)]))

	@classmethod
	def Cap(cls, obj: Cap, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
		res = cls.resolve(obj.child, grammar, ctx)
		ctx.sp.state.groupdict[obj.name] = len(ctx.sp.state.groupdict) + 1
		return res

	@classmethod
	def Spacer(cls, obj: Spacer, grammar: Grammar, ctx: typing.Any = None) -> str:
		pass

	@classmethod
	def Comment(cls, obj: Comment, grammar: Grammar, ctx: typing.Any = None) -> str:
		pass

	@classmethod
	def MultiLineComment(cls, obj: MultiLineComment, grammar: Grammar, ctx: typing.Any = None) -> str:
		pass

	@classmethod
	def Ref(cls, obj: Ref, grammar: Grammar, ctx: typing.Any = None):
		##ic(ctx.refsPtrs, obj.name)
		#return ctx.refsPtrs[obj.name]
		return obj

	@classmethod
	def CharClass(cls, obj: CharClass, grammar: Grammar, ctx: typing.Any = None):
		return (sc.IN, [c for c in obj.chars])

	@classmethod
	def WellKnownChars(cls, obj: WellKnownChars, grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.CATEGORY, wellKnownRegExpInvRemapSingle[obj])

	@classmethod
	def CharClassUnion(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.IN, [obj])

	@classmethod
	def CharRange(cls, obj: CharRange, grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.RANGE, (obj.start, obj.stop))

	@classmethod
	def _wrapAlts(cls, alts: typing.Iterable[str], grammar: Grammar, ctx: typing.Any = None) -> str:
		return (sc.IN, list(alts))

	@classmethod
	def preprocessGrammar(cls, grammar: Grammar, ctx: typing.Any = None) -> None:
		pass

	@classmethod
	def _transpile(cls, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
		cls.embedGrammar(grammar, ctx)
		for secName in cls.getOrder(grammar):
			if not ctx.dict[secName]:
				del ctx.dict[secName]
		#ic(ctx.sp)

		return (cls.unparseRx(res),)

	@classmethod
	def unparseRx(cls, rx, ctx) -> str:
		raise NotImplementedError

	@classmethod
	def getOrder(cls, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
		return ("chars", "keywords", "tokens", "fragmented", "prods")

	@classmethod
	def embedGrammar(cls, obj: Grammar, ctx: typing.Any = None) -> None:
		for secName in cls.getOrder(obj):
			sec = getattr(obj, secName)
			secSeq = ctx.dict.get(secName, None)
			if secSeq is None:
				ctx.dict[secName] = secSeq = []
			res = cls.resolve(sec, obj, ctx)
			#ic(res)
			res = cls.refsDelayedResolve(res, ctx)
			#ic(res)
			secSeq.extend(res)

	@classmethod
	def refsDelayedResolve(cls, seq, ctx: typing.Any = None):
		newSeq = []
		for el in seq:
			#ic(el)
			if isinstance(el, Ref):
				elRes = cls.refsDelayedResolve(ctx.refsPtrs[el.name], ctx)
				#ic(elRes)
			elif isinstance(el, (tuple, list)):
				elRes = cls.refsDelayedResolve(el, ctx)
			else:
				elRes = el

			newSeq.append(elRes)

		return type(seq)(newSeq)
