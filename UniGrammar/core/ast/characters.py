import string
import typing
from abc import ABC, abstractmethod

from charRanges import multiRSub, setToRanges

from .base import ASTNodeLayer, Container, Node, Ref, Wrapper

#maxUnicodeCodePoint = 0x10FFFF
maxUnicodeCodePoint = 0xFF


class _CharClass(ABC):
	__slots__ = ()

	def __init__(self, negative: bool) -> None:
		self.negative = negative  # pylint: disable=assigning-non-slot

	@abstractmethod
	def getRanges(self, grammar=None):
		raise NotImplementedError

	def __hash__(self):
		return hash(tuple(self.getRanges()))

	def __eq__(self, other):
		return tuple(self.getRanges()) == tuple(other.getRanges())

	def toPositiveUnion(self, grammar, base=None) -> "CharClassUnion":
		ranges = list(self.getRanges(grammar))
		if self.negative:
			if base is None:
				base = range(0, maxUnicodeCodePoint + 1)

			ranges = multiRSub(ranges, base)
		return CharClassUnion(*(CharRange.fromRange(r) for r in ranges))


class CharClass(Node, _CharClass):
	__slots__ = ("chars", "negative")

	NODE_LAYER = ASTNodeLayer.charClass

	def __init__(self, chars: str, negative: bool = False) -> None:
		Node.__init__(self)
		_CharClass.__init__(self, negative)
		self.chars = chars

	def getRanges(self, grammar: None = None) -> typing.Iterator[range]:
		for c in self.chars:
			c = ord(c)
			yield range(c, c + 1)

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.chars) + ", " + repr(self.negative) + ")"


wellKnown = {}


def getWellKnown(k: str) -> _CharClass:
	res = wellKnown.get(k, None)
	if res is None:
		el = getattr(string, k)
		if isinstance(el, str):
			res = tuple(CharRange.fromBounds(el.start, el.stop - 1) for el in setToRanges(el))
			if len(res) == 1:
				res = res[0]
			else:
				res = CharClassUnion(*res)

			wellKnown[k] = res
	return res


class WellKnownChars(Wrapper, _CharClass):
	__slots__ = ("name",)

	NODE_LAYER = ASTNodeLayer.charClass

	def __init__(self, name: str, negative: bool = False) -> None:  # pylint: disable=super-init-not-called
		self.name = name
		res = getWellKnown(name)
		if negative:
			res = CharClassUnion(res, negative=True)

		Wrapper.__init__(self, res)  # fucking `super` doesn't wor well in the case of multiple inheritance

	def getRanges(self, grammar: None = None) -> typing.Iterator[range]:
		return self.child.getRanges()

	@property
	def negative(self):
		return self.child.negative

	@negative.setter
	def negative(self, v):
		self.child.negative = v

	def __hash__(self):
		return hash(self.child)

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.name) + ", " + repr(self.child) + ")"


class CharRange(Node, _CharClass):
	__slots__ = ("range", "negative")

	NODE_LAYER = ASTNodeLayer.charClass

	def __init__(self, rng: range, negative: bool = False) -> None:
		Node.__init__(self)
		_CharClass.__init__(self, negative)
		self.range = rng

	@classmethod
	def fromBounds(cls, start: str, stop: str, negative: bool = False):
		return cls(range(ord(start) if not isinstance(start, int) else start, (ord(stop) if not isinstance(stop, int) else stop) + 1), )

	@classmethod
	def fromRange(cls, rng: range, negative: bool = False):
		res = cls(None, negative)
		res.range = rng
		return res

	@property
	def start(self) -> str:
		return chr(self.range.start)

	@property
	def end(self) -> str:
		"""INCLUSIVE!"""
		return chr(self.range.stop - 1)

	def getRanges(self, grammar: None = None) -> typing.Iterator[range]:
		yield self.range

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.negative) + ", " + repr(self.range) + ")"


class CharClassUnion(Container, _CharClass):
	__slots__ = ("negative",)

	EMPTY_MAKES_SENSE = True
	NODE_LAYER = ASTNodeLayer.charClass
	FOR_NODES_OF_LAYER = ASTNodeLayer.charClass

	def __init__(self, *children, negative=False) -> None:
		Container.__init__(self, *children)
		_CharClass.__init__(self, negative)

	def getRanges(self, grammar: typing.Optional["Grammar"] = None) -> None:
		for c in self.children:
			if isinstance(c, Ref):
				yield from grammar.chars.index[c.name].getRanges(grammar)
			else:
				yield from c.getRanges(grammar)

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.negative) + ", " + repr(self.children) + ")"
