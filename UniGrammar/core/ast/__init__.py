import typing
from collections.abc import Iterable
from pathlib import Path

from ..testing import TestingSpec
from .base import ASTNodeLayer, Collection, Name, Node, Wrapper

StrOrListOfStrs = typing.Union[str, typing.Iterable[str]]


class CosmeticNode(Node):
	__slots__ = ()


class Spacer(CosmeticNode):
	__slots__ = ("count",)

	NODE_LAYER = ASTNodeLayer.any

	def __init__(self, count: int = 1) -> None:
		super().__init__()
		self.count = count


class Comment(CosmeticNode):
	"""A comment"""

	NODE_LAYER = ASTNodeLayer.any

	__slots__ = ("value",)

	def __init__(self, value: str) -> None:
		super().__init__()
		self.value = value


class MultiLineComment(Comment):
	"""A multiline comment"""

	__slots__ = ()

	def __init__(self, value: str) -> None:
		if isinstance(value, str):
			value = value.split("\n")
		else:
			value = tuple(value)
		super().__init__(value)


class Section(Collection):
	__slots__ = ("index",)

	NODE_LAYER = ASTNodeLayer.grammar

	EMPTY_MAKES_SENSE = True

	def __init__(self, children: typing.List[Name] = ()) -> None:
		super().__init__(children)
		self.index = None

	def embed(self, another: "Section") -> None:
		if another is not None:
			self.children += another.children

	def __iadd__(self, another: "Section") -> "Section":
		self.embed(another)
		return self

	def recomputeIndex(self) -> None:
		self.index = {n.name: n.child for n in self.children if isinstance(n, Name)}

	def findFirstRule(self) -> typing.Optional[Name]:
		for r in self.children:
			if isinstance(r, Name):
				return r
		return None


class Characters(Section):
	__slots__ = ()

	FOR_NODES_OF_LAYER = ASTNodeLayer.charClass

	def __init__(self, children: typing.List[Name] = ()) -> None:
		super().__init__(children)
		self.recomputeIndex()


class Tokens(Section):
	__slots__ = ()
	FOR_NODES_OF_LAYER = ASTNodeLayer.token


class Keywords(Tokens):
	__slots__ = ()
	FOR_NODES_OF_LAYER = ASTNodeLayer.keyword


class Productions(Section):
	__slots__ = ()
	FOR_NODES_OF_LAYER = ASTNodeLayer.production


class Fragmented(Productions):
	__slots__ = ()
	FOR_NODES_OF_LAYER = ASTNodeLayer.fragment


class GrammarMeta:
	__slots__ = ("id", "title", "license", "doc", "docRef", "filenameRegExp", "cls")

	NODE_LAYER = ASTNodeLayer.grammar

	def __init__(self, iD: str, title: str, licence: str, doc: typing.Optional[str], docRef: typing.Optional[StrOrListOfStrs], filenameRegExp: typing.Optional[StrOrListOfStrs], cls=None) -> None:  # pylint:disable=too-many-arguments
		self.id = iD
		self.title = title
		self.license = licence
		self.doc = doc
		self.docRef = docRef
		self.filenameRegExp = filenameRegExp
		self.cls = cls

	def __repr__(self):
		return self.__class__.__name__ + "(" + ", ".join(repr(k) + "=" + repr(getattr(self, k)) for k in __class__.__slots__) + ")"  # pylint:disable=undefined-variable


def GrammarInitSignature(self, *, meta: GrammarMeta, tests: typing.Iterable[TestingSpec] = None, chars: typing.Optional[Characters] = None, keywords: typing.Optional[Keywords] = None, tokens: typing.Optional[Tokens] = None, fragmented: typing.Optional[Fragmented] = None, prods: typing.Optional[Productions] = None) -> None:  # pylint: disable=unused-argument
	pass


def _genSectionDescriptors(*initialDescriptors):
	sectionsDescriptors = tuple(sorted(initialDescriptors, key=lambda d: d[1].FOR_NODES_OF_LAYER))

	offset = 0 - sectionsDescriptors[0][1].FOR_NODES_OF_LAYER
	for idx, d in enumerate(sectionsDescriptors):
		thisDescrForNodesOfLevel = d[1].FOR_NODES_OF_LAYER
		thisDescrOffset = idx - thisDescrForNodesOfLevel
		assert offset == thisDescrOffset, "In Grammar we also use node layers as indices. So all the descriptors must have the same offset. The first one had offset of " + str(offset) + ", but " + str(d) + " (" + str(thisDescrForNodesOfLevel) + ") has offset of " + str(thisDescrOffset)
	return sectionsDescriptors, offset


class Grammar(Node, Iterable):
	sectionsDescriptors, SESSION_DESCRIPTOR_OFFSET = _genSectionDescriptors(("chars", Characters), ("keywords", Keywords), ("tokens", Tokens), ("fragmented", Fragmented), ("prods", Productions))
	__slots__ = ("meta", "tests") + tuple(s[0] for s in sectionsDescriptors)

	NODE_LAYER = ASTNodeLayer.grammar
	FOR_NODES_OF_LAYER = ASTNodeLayer.grammar

	EMPTY_MAKES_SENSE = True

	def __init__(self, *, meta: GrammarMeta, tests: typing.Iterable[TestingSpec] = None, **sections) -> None:
		super().__init__()
		self.meta = meta
		self.tests = tests

		for k, typ in self.__class__.sectionsDescriptors:
			v = sections.get(k, None)
			if v is None:
				v = typ()
			setattr(self, k, v)

	__init__.__wraps__ = GrammarInitSignature

	def embed(self, another: "Grammar") -> None:
		for name, typ in self.__class__.sectionsDescriptors:  # pylint:disable=unused-variable
			v = getattr(self, name)
			v1 = getattr(another, name)
			v += v1

	def __iadd__(self, another: "Grammar") -> "Grammar":
		self.embed(another)
		return self

	def __iter__(self):
		for k, typ in self.__class__.sectionsDescriptors:  # pylint:disable=unused-variable
			yield getattr(self, k)

	def __len__(self) -> int:
		return len(self.__class__.sectionsDescriptors)

	def __getitem__(self, k: int) -> Section:
		return getattr(self, self.__class__.sectionsDescriptors[k + self.__class__.SESSION_DESCRIPTOR_OFFSET][0])

	def __setitem__(self, k, v):
		return setattr(self, self.__class__.sectionsDescriptors[k + self.__class__.SESSION_DESCRIPTOR_OFFSET][0], v)


class Import(Node):
	"""Used to represent imported grammars for backends supporting submodules. Transpiled into import statements and generates subgrammar files for them. Fr the backends not supporting imports just merges the contents."""

	NODE_LAYER = ASTNodeLayer.grammar

	__slots__ = ("file",)

	def __init__(self, file: Path):
		super().__init__()
		self.file = file


class Embed(Wrapper):
	"""Used to represent imported subgrammars, which content must be merged to the current grammar. Can be produced by either imports, or by templates invocations"""

	NODE_LAYER = ASTNodeLayer.grammar

	__slots__ = ()
