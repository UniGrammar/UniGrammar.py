import typing
from collections.abc import Iterable
from enum import IntEnum


class ASTNodeLayer(IntEnum):
	any = 0
	charClass = 1
	keyword = 2
	token = 3
	fragment = 4
	production = 5
	grammar = 6


class Node:
	"""Just a node of our AST"""

	__slots__ = ()

	NODE_LAYER = None  # type: ASTNodeLayer **Lower bound** of node layer
	STACK_INVISIBLE = False  # type: bool Whether this node appear within stack
	AST_INVISIBLE = False  # type: bool Whether this node causes an AST node be generated

	def getLayer(self, grammar: "Grammar" = None) -> ASTNodeLayer:
		"""Return real node layer"""
		return self.__class__.NODE_LAYER

	def __init__(self) -> None:
		pass


class Collection(Node, Iterable):
	"""A node of AST that can have multiple children"""

	EMPTY_MAKES_SENSE = False
	FOR_NODES_OF_LAYER = None  # type: ASTNodeLayer **Upper bound** of layers of children

	__slots__ = ("children",)

	def getLayer(self, grammar: "Grammar" = None) -> ASTNodeLayer:
		return max(max(el.getLayer(grammar) for el in self.children), self.__class__.NODE_LAYER)

	def __init__(self, children: Node) -> None:
		super().__init__()
		self.children = children

	def __len__(self) -> int:
		return len(self.children)

	def __iter__(self) -> typing.Iterable[Node]:
		yield from self.children

	def __getitem__(self, k: int) -> Node:
		return self.children[k]

	def __setitem__(self, k, v):
		self.children[k] = v

	def __delitem__(self, k):
		del self.children[k]

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.children) + ")"


class Wrapper(Node):
	"""A node of AST which has exactly one child"""

	__slots__ = ("child",)

	def getLayer(self, grammar: "Grammar" = None) -> ASTNodeLayer:
		return max(self.child.getLayer(grammar), self.__class__.NODE_LAYER)

	def getASTVisibleChild(self):
		n = self.child
		while isinstance(n, __class__) and n.__class__.AST_INVISIBLE:
			n = n.child

		return n

	def __init__(self, child: Node) -> None:
		super().__init__()
		self.child = child

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.child) + ")"


class Container(Collection):
	__slots__ = ()

	def __init__(self, *children) -> None:
		super().__init__(children)

	def __repr__(self):
		return self.__class__.__name__ + "(" + ", ".join(repr(el) for el in self.children) + ")"


class Name(Wrapper):
	"""Assigns a name/id to a (non-)terminal"""

	__slots__ = ("name",)

	NODE_LAYER = ASTNodeLayer.grammar

	def __init__(self, name: str, child: Node) -> None:
		self.name = name
		super().__init__(child)

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.name) + ", " + repr(self.child) + ")"


class Ref(Node):
	"""Represents a reference to another (non-)terminal"""

	__slots__ = ("name",)

	NODE_LAYER = ASTNodeLayer.any

	def getLayer(self, grammar: "Grammar" = None) -> ASTNodeLayer:
		if grammar is None:
			raise NotImplementedError("it is a reference. So we need to be able to resolve it in a grammar to properly get its layer")

		raise NotImplementedError

	def __init__(self, name: Node) -> None:
		super().__init__()
		self.name = name

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.name) + ")"


class Group(Wrapper):
	"""A group is just an associative entity for grammar DSL syntax purposes, like `(a b)*` means that sequence of a and b repeats.
	This node allows forcing creation of a group. It is used for internal purposes and usually is not exposed.
	"""

	STACK_INVISIBLE = True
	AST_INVISIBLE = True

	__slots__ = ()

	NODE_LAYER = ASTNodeLayer.any
