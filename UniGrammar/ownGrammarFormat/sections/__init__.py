__all__ = ("CharacterClassParser", "KeywordsParser", "TokensParser", "ProductionsParser", "FragmentedParser", "parseChars", "parseKeywords", "parseTokens", "parseProductions", "parseFragmented")

import typing

from ...core.ast import Characters, Fragmented, Keywords, Productions, Tokens
from ...core.ast.base import Node
from .. import nodes
from ..core import IShittyParser
from ..nodes import *
from ..nodes.modifiers import *


class CharacterClassParser(IShittyParser):
	"""Parses tokens"""

	__slots__ = ()
	SEC_NAME = "chars"
	NODES = (Characters,)

	DISTINCTIVE_SET = (
		parseRangeCharClass,
		parseWellKnownCharClass,
		parseLitCharClass,
		parseAltCharClass,
		parseRef,
	)

	MODIFIERS = (processNegativeCharClassModifier,)

	def wrapResults(self, rec: typing.Mapping[str, typing.Any], results: Node) -> Node:
		neg = rec.get("negative", False)
		return CharClassUnion(*results, negative=neg)


nodes.parseChars = parseChars = CharacterClassParser()


class KeywordsParser(IShittyParser):
	"""Parses keywords"""

	__slots__ = ()
	SEC_NAME = "keywords"
	NODES = (Keywords,)

	DISTINCTIVE_SET = (parseAlt, parseLitKeywords)
	MODIFIERS = ()


parseKeywords = KeywordsParser()


def assertNoLitTokens(rec: typing.Dict[str, typing.Union[str, int]], recordParser: "IShittyParser") -> None:
	lit = rec.get("lit", None)
	if lit is not None:
		belongsTo = "keywords" if len(lit) > 1 else "chars"
		raise ValueError("`lit` belongs to `" + belongsTo + "`!")


class TokensParser(IShittyParser):
	"""Parses tokens"""

	__slots__ = ()
	SEC_NAME = "tokens"
	NODES = (Tokens,)

	DISTINCTIVE_SET = (
		parseRef,
		parseAlt,
		parseSeq,
		parseOpt,
		parseUnCap,
		assertNoLitTokens,
	)
	MODIFIERS = (processMinModifier, processPreferModifier)


parseTokens = TokensParser()


class ProductionsParser(TokensParser):
	"""Parses productions"""

	__slots__ = ()
	SEC_NAME = "prods"
	NODES = (Productions,)

	DISTINCTIVE_SET = TokensParser.DISTINCTIVE_SET + (parseTemplateInstantiation,)
	MODIFIERS = TokensParser.MODIFIERS + (processCapModifier,)


parseProductions = ProductionsParser()


class FragmentedParser(ProductionsParser):
	__slots__ = ()
	SEC_NAME = "fragmented"
	NODES = (Fragmented,)


parseFragmented = FragmentedParser()
