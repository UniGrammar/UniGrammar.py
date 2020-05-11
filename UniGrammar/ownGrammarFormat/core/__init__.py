import typing
from abc import ABC, abstractmethod

from ...core.ast import Comment, Section, Spacer
from ...core.ast.base import Name, Node, Ref


class SectionRecordParsingShit(ABC):  # pylint: disable=too-few-public-methods
	__slots__ = ()
	NODES = None

	@property
	def NODE(self) -> Node:
		return self.__class__.NODES[0]  # pylint:disable=unsubscriptable-object


class SectionRecordParser(SectionRecordParsingShit):
	__slots__ = ()

	@abstractmethod
	def __call__(self, rec: typing.Mapping[str, typing.Any], recordParser: "IShittyParser") -> typing.Optional[Node]:
		raise NotImplementedError()


class SectionSubRecordSingleParamParser(SectionRecordParsingShit):
	ATTR_NAME = None

	def param(self, rec: typing.Mapping[str, typing.Any]) -> typing.Any:
		return rec.get(self.__class__.ATTR_NAME, None)

	@abstractmethod
	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: "IShittyParser") -> Node:
		raise NotImplementedError()

	def __call__(self, rec: typing.Mapping[str, typing.Any], recordParser: "IShittyParser") -> typing.Optional[Node]:
		param = self.param(rec)
		if param is not None:
			res = self.apply(param, rec, recordParser)
			if res is None:
				raise ValueError("`apply` returned None", self, rec)
			return res
		return None


class SectionRecordModifier(SectionRecordParsingShit):
	__slots__ = ()

	@abstractmethod
	def __call__(self, rec: typing.Mapping[str, typing.Any], res) -> Node:
		raise NotImplementedError()


class SectionRecordSingleParamModifier(SectionRecordModifier):
	__slots__ = ()

	ATTR_NAME = None

	def param(self, rec: typing.Mapping[str, typing.Any]) -> typing.Optional[typing.Union[str, int]]:
		return rec.get(self.__class__.ATTR_NAME, None)

	@abstractmethod
	def apply(self, param: str, res: Node):
		raise NotImplementedError()

	def __call__(self, rec: typing.Mapping[str, typing.Any], res: Node) -> Node:
		param = self.param(rec)
		if param is not None:
			res = self.apply(param, res)
		return res


class IShittyParser(SectionRecordParsingShit):
	"""Encapsulates code parsing a specific section items."""

	__slots__ = ()

	SEC_NAME = None
	DISTINCTIVE_SET = None  # each el can be from this DISTINCTIVE_SET
	MODIFIERS = None

	def tryParseDistinctiveSet(self, rec: typing.Mapping[str, typing.Any]) -> typing.Iterable[Node]:
		return tuple(el for el in (func(rec, self) for func in self.__class__.DISTINCTIVE_SET) if el)  # pylint:disable=not-an-iterable

	def wrapResult(self, rec: typing.Mapping[str, typing.Any], res: Node) -> Node:
		"""Transforms an item into an actual AST subtree"""
		for modifierProcessor in self.__class__.MODIFIERS:  # pylint:disable=not-an-iterable
			res = modifierProcessor(rec, res)

		return res

	def wrapResults(self, rec: typing.Mapping[str, typing.Any], results: Node) -> Node:  # pylint: disable=no-self-use
		"""Transforms multiple items within single item into an actual AST subtree"""
		raise ValueError("You must choose something.", len(results), results)

	def __call__(self, rec: typing.Mapping[str, typing.Any]) -> Node:
		"""Parses an item in a section"""
		if not isinstance(rec, dict):
			raise ValueError("A record " + repr(rec) + " must be a dict specifying its properties")
		results = self.tryParseDistinctiveSet(rec)

		if len(results) == 1:
			res = results[0]
			if res:
				return self.wrapResult(rec, res)
			else:
				raise ValueError("the result is None")
		elif len(results) > 1:
			return self.wrapResults(rec, results)
		else:
			raise ValueError("Nothing has parsed from a record in `" + self.__class__.SEC_NAME + "` section", rec)

	def _parseSection(self, chars: typing.Mapping[str, typing.Any]) -> typing.Iterator[Name]:
		"""Parses a section using a parser"""
		for rec in chars:
			rid = rec.get("id")
			if rid:
				yield Name(rec["id"], self(rec))
			else:
				yield from parseNeutral(rec)

	def parseSection(self, rootDic: typing.Mapping[str, typing.Any]) -> Section:
		items = list(self._parseSection(rootDic.get(self.__class__.SEC_NAME, ())))
		return self.NODE(items)


NeutralNode = typing.Union[Spacer, Comment]


class SpacerParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Spacer,)
	ATTR_NAME = "spacer"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Spacer:
		if isinstance(param, int):
			if param > 0:
				return self.NODE(param)
			else:
				raise ValueError("`" + self.__class__.ATTR_NAME + "` is a count of blank lines. It cannot be negative", param)
		else:
			raise ValueError("`" + self.__class__.ATTR_NAME + "` must be an integer", param)


parseSpacer = SpacerParser()


class CommentParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Comment,)
	ATTR_NAME = "comment"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Comment:
		if isinstance(param, str):
			return self.NODE(param)
		else:
			raise ValueError("`" + self.__class__.ATTR_NAME + "` must be an string", param)


parseComment = CommentParser()


def parseNeutral(rec: typing.Dict[str, int]) -> typing.Iterator[NeutralNode]:
	"""Parses AST nodes that can belong to any section"""
	for f in (parseSpacer, parseComment):
		res = f(rec, None)
		if res is not None:
			yield res
