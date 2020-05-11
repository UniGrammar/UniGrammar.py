import typing
from abc import ABC, abstractmethod

from charRanges import ranges2CharClassRangedString

from .ast import Grammar
from .ast.characters import CharClass, CharClassUnion, CharRange, _CharClass
from .backend.Generator import Generator


class CharRangeProcessor(ABC):
	__slots__ = ()

	@abstractmethod
	def __call__(self, classProcessor: "CharClassProcessor", backend: typing.Type[Generator], obj: CharRange, grammar: Grammar) -> str:
		raise NotImplementedError


class StandaloneCharRangeProcessor(CharRangeProcessor):
	__slots__ = ("separator",)

	def __init__(self, separator: str):
		self.separator = separator

	def __call__(self, classProcessor: "CharClassProcessor", backend: typing.Type[Generator], obj: CharRange, grammar: Grammar) -> str:
		return classProcessor.wrapNegativeOuter(obj, self.separator.join((backend.wrapLiteralChar(obj.start), backend.wrapLiteralChar(obj.end))))


class RegExpLikeCharRangeProcessor(CharRangeProcessor):
	__slots__ = ()

	def __call__(self, classProcessor: "CharClassProcessor", backend: typing.Type[Generator], obj: CharRange, grammar: Grammar) -> str:
		return classProcessor.wrapNegativeOuter(obj, classProcessor.encloseCharClass(classProcessor.charRangeSeparatorInClass.join((obj.start, obj.end)), obj, grammar))


regExpLikeCharRangeProcessor = RegExpLikeCharRangeProcessor()


class CharClassProcessor(ABC):
	charClassSetStart = None
	charClassSetEnd = None
	charRangeSeparatorInClass = "-"

	@classmethod
	@abstractmethod
	def union(cls, backend, union, grammar):
		raise NotImplementedError()

	@classmethod
	def encloseCharClass(cls, s: str, obj: _CharClass, grammar: Grammar) -> str:
		return cls.charClassSetStart + s + cls.charClassSetEnd

	@classmethod
	@abstractmethod
	def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
		raise NotImplementedError

	@classmethod
	@abstractmethod
	def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
		raise NotImplementedError

	@classmethod
	def wrapCharClass(cls, backend: typing.Type[Generator], s: str, obj: _CharClass, grammar: Grammar) -> str:
		return cls.wrapNegativeOuter(obj, cls.encloseCharClass(cls.wrapNegativeInner(obj, s), obj, grammar))

	range = classmethod(StandaloneCharRangeProcessor(".."))


class CharClassMergeProcessor(CharClassProcessor):
	charClassSetStart = "["
	charClassSetEnd = "]"

	@classmethod
	def union(cls, backend: typing.Type[Generator], union: CharClassUnion, grammar: Grammar) -> str:
		return cls.wrapCharClass(backend, ranges2CharClassRangedString(union.getRanges(grammar), escaper=backend.charClassEscaper), union, grammar)

	@classmethod
	def wrapNegativeOuter(cls, obj: typing.Union[CharClassUnion, CharClass], s: str) -> str:
		return s

	@classmethod
	def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s: str) -> str:
		return ("^" if obj.negative else "") + s

	range = classmethod(regExpLikeCharRangeProcessor)


class CharClassKeepProcessor(CharClassProcessor):  # pylint:disable=abstract-method
	charClassNegativeJoiner = None
	charClassPositiveJoiner = None
	charClassSetStart = '"'
	charClassSetEnd = '"'

	@classmethod
	def union(cls, backend: typing.Type[Generator], union: CharClassUnion, grammar: Grammar) -> str:
		joiner = cls.selectJoiner(union)
		if joiner is not None:
			return cls.wrapNegativeOuter(union, joiner.join(backend.resolve(c, grammar) for c in union.children))
		else:
			pu = union.toPositiveUnion(grammar)
			return cls.union(backend, pu, grammar)

	@classmethod
	def wrapNegativeInner(cls, obj: typing.Union[CharClassUnion, CharClass], s) -> str:
		return s

	@classmethod
	def selectJoiner(cls, union: CharClassUnion) -> str:
		return cls.charClassNegativeJoiner if union.negative else cls.charClassPositiveJoiner
