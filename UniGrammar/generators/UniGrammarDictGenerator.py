import typing
from collections import OrderedDict
from pathlib import Path
from pprint import pprint

from UniGrammarRuntime.ToolMetadata import Product
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ..core.ast import Comment, Embed, Grammar, Import, MultiLineComment, Spacer
from ..core.ast.base import Node, Ref
from ..core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars, _CharClass
from ..core.ast.prods import Cap, Prefer
from ..core.ast.templates import TemplateInstantiation
from ..core.ast.tokens import Alt, Iter, Lit, Opt, Seq
from ..core.backend.Generator import Generator, GeneratorContext, TranspiledResult
from ..core.backend.Runner import Runner
from ..core.CharClassProcessor import CharClassMergeProcessor


class DictGeneratorContext(GeneratorContext):
	__slots__ = ("dict",)

	def __init__(self, currentProdName: typing.Optional[str]) -> None:
		self.dict = OrderedDict()
		super().__init__(currentProdName)


class UniGrammarDictGenerator(Generator):
	__slots__ = ()
	META = None
	charClassEscaper = None
	stringEscaper = None
	CONTEXT_CLASS = DictGeneratorContext

	@classmethod
	def getGreeting(cls, obj: Grammar):
		meta = OrderedDict()

		meta["id"] = None

		if obj.meta.title:
			meta["title"] = obj.meta.title

		if obj.meta.doc:
			meta["doc"] = obj.meta.doc

		if obj.meta.docRef:
			dr = obj.meta.docRef
			if isinstance(dr, str):
				dr = (dr,)
			meta["doc-ref"] = dr

		if obj.meta.filenameRegExp:
			meta["filename-regexp"] = obj.meta.filenameRegExp
		return meta

	@classmethod
	def getHeader(cls, obj: Grammar):
		return cls.getGreeting(obj)

	@classmethod
	def Section(cls, arr: typing.Any, grammar: Grammar, ctx: typing.Any = None):
		res = []
		for obj in arr.children:
			objRes = cls.resolve(obj, grammar, ctx)
			print(obj, objRes)
			res.append(objRes)
		return res

	@classmethod
	def Name(cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx: typing.Any = None) -> str:
		print(obj.name, repr(obj.child))
		res = OrderedDict((("id", obj.name),))
		res.update(cls.resolve(obj.child, grammar, ctx))
		return res

	@classmethod
	def _Seq(cls, arr: typing.Iterable[Node], grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"seq": [cls.resolve(c, grammar, ctx) for c in arr]}

	@classmethod
	def Lit(cls, obj: Lit, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"lit": obj.value}

	@classmethod
	def Iter(cls, obj: Iter, grammar: Grammar, ctx: typing.Any = None) -> str:
		res = cls.resolve(obj.child, grammar, ctx)
		res["min"] = obj.minCount
		return res

	@classmethod
	def Opt(cls, obj: Opt, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"opt": cls.resolve(obj.child, None, ctx)}

	@classmethod
	def Cap(cls, obj: Cap, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
		res = cls.resolve(obj.child, grammar, ctx)
		res["cap"] = obj.name
		return res

	@classmethod
	def Prefer(cls, obj: Prefer, grammar: Grammar, ctx: typing.Any = None) -> str:
		res = cls.resolve(obj.child, grammar, ctx)
		res["prefer"] = obj.preference
		return res

	@classmethod
	def Spacer(cls, obj: Spacer, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"spacer": obj.count}

	@classmethod
	def Comment(cls, obj: Comment, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"comment": obj.value}

	@classmethod
	def MultiLineComment(cls, obj: MultiLineComment, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"comment": obj.value}

	@classmethod
	def Ref(cls, obj: Ref, grammar: Grammar, ctx: typing.Any = None):
		return {"ref": obj.name}

	@classmethod
	def CharClass(cls, obj: CharClass, grammar: Grammar, ctx: typing.Any = None):
		return {"lit": "".join(obj.chars)}

	@classmethod
	def WellKnownChars(cls, obj: WellKnownChars, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"well-known": obj.name}

	@classmethod
	def CharClassUnion(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.Alt(obj, grammar, ctx=ctx)

	@classmethod
	def CharRange(cls, obj: CharRange, grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"range": [obj.start, obj.stop]}

	@classmethod
	def _wrapAlts(cls, alts: typing.Iterable[str], grammar: Grammar, ctx: typing.Any = None) -> str:
		return {"alt": list(alts)}

	@classmethod
	def preprocessGrammar(cls, grammar: Grammar, ctx: typing.Any = None) -> None:
		pass

	@classmethod
	def TemplateInstantiation(cls, obj: TemplateInstantiation, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		res = {
			"template": obj.template,
		}
		return res

	@classmethod
	def _Import(cls, obj: Embed, embedIntermediateRepr: typing.Any, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	def Import(cls, obj: Import, ctx: typing.Any = None) -> typing.Any:
		return repr(obj)

	@classmethod
	def _transpile(cls, grammar: Grammar, ctx: typing.Any = None) -> typing.Iterable[str]:
		ctx.dict["meta"] = cls.getHeader(grammar)
		cls.embedGrammar(grammar, ctx)
		for secName in cls.getOrder(grammar):
			if not ctx.dict[secName]:
				del ctx.dict[secName]
		return ctx.dict

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
			secSeq.extend(cls.resolve(sec, obj, ctx))


def transpileToSerialized(grammar: Grammar, backend: Generator, serializer) -> str:
	"""Transpiles a unigrammar into a dict to be serialized to YAML, JSON, CBOR etc."""
	ctx = backend.initContext(grammar)
	backend.preprocessGrammar(grammar, ctx)
	dic = backend._transpile(grammar, ctx)
	return TranspiledResult(grammar.meta.id, serializer.unprocess(dic))
