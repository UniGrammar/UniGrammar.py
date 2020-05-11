__all__ = ("NegativeCharClassModifier", "MinModifier", "PreferModifier", "CapModifier", "processNegativeCharClassModifier", "processMinModifier", "processPreferModifier", "processCapModifier")

import typing

from ...core.ast.base import Node, Ref
from ...core.ast.characters import CharClass, CharClassUnion, WellKnownChars, _CharClass
from ...core.ast.prods import Cap, Prefer
from ...core.ast.tokens import Iter, Opt, Seq
from ..core import SectionRecordModifier, SectionRecordSingleParamModifier


class NegativeCharClassModifier(SectionRecordModifier):
	__slots__ = ()
	NODES = CharClassUnion, WellKnownChars, CharClass

	def __call__(self, rec: typing.Mapping[str, typing.Any], res: typing.Union[_CharClass, Ref]) -> _CharClass:
		neg = rec.get("negative", False)

		if isinstance(res, WellKnownChars):
			res.negative = res.negative != neg
		elif isinstance(res, Ref):
			return CharClassUnion(res, negative=neg)
		else:
			res.negative = neg  # we never get negative=True here (because we parse so), so we need to set it
		return res


processNegativeCharClassModifier = NegativeCharClassModifier()


class MinModifier(SectionRecordSingleParamModifier):
	__slots__ = ()
	NODES = (Iter,)
	ATTR_NAME = "min"

	def apply(self, param: int, res: Node) -> Node:
		if isinstance(param, int) and param >= 0:
			return Iter(res, param)
		else:
			raise ValueError("`min` must be a nonnegative `int`")


processMinModifier = MinModifier()


validPreferences = frozenset(("shift", "reduce"))
validTypesForPreference = (Seq, Iter, Opt)


class PreferModifier(SectionRecordSingleParamModifier):
	__slots__ = ()
	NODES = (Prefer,)
	ATTR_NAME = "prefer"

	def apply(self, param: str, res: Node) -> Node:
		if isinstance(param, str) and param in validPreferences:
			if isinstance(res, validTypesForPreference):
				return Prefer(res, param)
			else:
				raise ValueError("You cannot use `prefer` for `" + type(res).__name__ + "`")
		else:
			raise ValueError("`prefer` must be from " + repr(validPreferences) + " but `" + repr(param) + "` is given.")


processPreferModifier = PreferModifier()


class CapModifier(SectionRecordSingleParamModifier):
	__slots__ = ()
	NODES = (Cap,)
	ATTR_NAME = "cap"

	def apply(self, param: str, res: Node) -> Node:
		if isinstance(param, str) and param:
			if isinstance(res, Iter):
				raise ValueError("Don't iterate (`min`) a `cap`, or in ANTLR you will face issues capturing the properties of each iterated entity by name in a generic way. Put the iterated content into a separate rule.")
			return Cap(param, res)
		else:
			raise ValueError("`cap` must be a valid name")


processCapModifier = CapModifier()
