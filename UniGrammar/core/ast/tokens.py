import typing

from .base import ASTNodeLayer, Container, Node, Ref, Wrapper


class Seq(Container):
	"""Represents a sequence of (non-)terminals"""

	NODE_LAYER = ASTNodeLayer.token
	FOR_NODES_OF_LAYER = ASTNodeLayer.production

	__slots__ = ()


class Lit(Node):
	"""Literal, just a string. Usually a keyword."""

	__slots__ = ("value",)

	NODE_LAYER = ASTNodeLayer.charClass

	def getLayer(self, grammar: "Grammar" = None) -> ASTNodeLayer:
		if len(self.value) > 1:
			return ASTNodeLayer.keyword
		return ASTNodeLayer.charClass

	def __init__(self, value: str) -> None:
		super().__init__()
		self.value = value


class Alt(Container):
	"""Represents an alternative."""

	NODE_LAYER = ASTNodeLayer.token
	FOR_NODES_OF_LAYER = ASTNodeLayer.production

	__slots__ = ()


class Opt(Wrapper):
	"""Represents optionality. We could have introduced `max` for `Iter` instead (max=1 and min=0 replacing this node), but
	* parser generators usually have a distinct syntax node for optionality (usually `?`) and have no syntax for maximal count, so it would require us to detect this situation and work around it and process its interaction to `min` correctly
	* this would be not very semantically correct to represent presence/absence of a single node with a collection
	So we have the both options. See `Iter.toHardcode` for more info."""

	NODE_LAYER = ASTNodeLayer.token

	__slots__ = ()


class Iter(Wrapper):
	"""Represents repeats. A child must be repeated at least `minCount` times and at most `maxCount` times."""

	NODE_LAYER = ASTNodeLayer.token

	__slots__ = ("minCount", "maxCount")

	@property
	def slice(self):
		return slice(self.minCount, self.maxCount, 1)

	def __init__(self, child: typing.Union[Ref, str], minCount: int, maxCount: typing.Optional[int] = None) -> None:
		assert 0 <= minCount
		assert not maxCount or minCount < maxCount
		if minCount == 0:
			if maxCount == 1:
				raise ValueError("You must use `Opt` for this")

		super().__init__(child)
		self.minCount = minCount
		self.maxCount = maxCount

	def toHardcode(self) -> Seq:
		if self.maxCount is None:
			raise NotImplementedError("It is impossible to transform this node into hardcoded sequence")

		return Seq([self.child] * self.minCount + [Opt(self.child)] * (self.maxCount - self.minCount))
