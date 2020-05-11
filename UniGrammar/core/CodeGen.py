import typing
from abc import ABC, abstractmethod

from .ast import Grammar
from .ast.base import Ref
from .ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from .ast.prods import Cap
from .ast.templates import TemplateInstantiation
from .ast.tokens import Alt, Iter, Lit, Opt, Seq


class CodeGenContext:
	__slots_ = ("currentProdName",)

	def __init__(self, currentProdName: typing.Optional[str]) -> None:
		self.currentProdName = currentProdName

	def spawn(self):
		"""Spawns a new context object, partially independent from this one. It's you to decide which fields are passed by reference and which are deepcopied. Override it in all derived classes if you need something to be deepcopied into child context"""
		return self.__class__(self.currentProdName)

	def __repr__(self):
		return self.__class__.__name__ + "<" + self.currentProdName + ">"


class CodeGen(ABC):
	__slots__ = ()

	@classmethod
	def Ref(cls, obj: Ref, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> str:
		return obj.name

	@classmethod
	@abstractmethod
	def Name(cls, obj: typing.Any, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Lit(cls, obj: Lit, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Iter(cls, obj: Iter, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Opt(cls, obj: Opt, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Cap(cls, obj: Cap, grammar: typing.Optional[Grammar], ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def CharClass(cls, obj: CharClass, grammar) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def WellKnownChars(cls, obj: WellKnownChars, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def CharClassUnion(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def CharRange(cls, obj: CharRange, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError

	@classmethod
	@abstractmethod
	def embedGrammar(cls, obj: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Alt(cls, obj: Alt, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def Seq(cls, obj: Seq, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	@abstractmethod
	def TemplateInstantiation(cls, obj: TemplateInstantiation, grammar: Grammar, ctx: typing.Any = None) -> typing.Any:
		raise NotImplementedError()

	@classmethod
	def initContext(cls, grammar):
		return CodeGenContext(None)
