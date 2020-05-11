import typing
from collections.abc import Iterable, Mapping
from warnings import warn

from . import Grammar
from .base import Name, Node, Ref, Wrapper


def walkAST(node: Node, funcToCall: typing.Callable, parent: typing.Optional[Node] = None, shouldTrace: typing.Callable = False) -> None:
	"""Walks AST leaves, calling funcToCall on all of them.
	`funcToCall` must return a tuple
	1. a `bool`, telling if we should deepen into `Container`s and `Wrapper`s
	2. a `Node`, giving replacement to the current node. `None` means "delete the node". If you want to do nothing, return the same node.
	3. a `bool` telling if we should crawl the replacement.

	Usually you need return True, node, False"""

	if callable(shouldTrace):
		_shouldTrace = shouldTrace(node, parent)
	else:
		_shouldTrace = shouldTrace

	if _shouldTrace:
		print("walkAST", node, parent)

	shouldDeepen, replacement, shouldWalkReplacement = funcToCall(node, parent)

	if _shouldTrace and node is not replacement:
		print("Node replaced", node, "->", replacement)
	node = replacement

	if shouldWalkReplacement:
		if node is not None:
			replacement = walkAST(node, funcToCall, parent, shouldTrace)
			if _shouldTrace and node is not replacement:
				print("Node replaced again", node, "->", replacement)
			node = replacement
		else:
			warn("When deleting a node, `shouldWalkReplacement` must be `False`: " + repr(node))

	if shouldDeepen:
		if isinstance(node, Iterable):
			if _shouldTrace:
				print("Processing children of ", node)
			for i in range(len(node)):
				v = node[i]
				childReplacement = walkAST(v, funcToCall, node, shouldTrace)
				if childReplacement is not None:
					if childReplacement is not v:
						if _shouldTrace:
							print(str(i) + "th child replaced", v, "->", childReplacement, node, parent)
						node[i] = childReplacement
				else:
					if _shouldTrace:
						print(str(i) + "th child deleted", v, node, parent)
					del node[i]
			if not len(node) and not node.EMPTY_MAKES_SENSE:
				if _shouldTrace:
					print("Empty collection deleted", node)
				return None
		elif isinstance(node, Wrapper):
			if _shouldTrace:
				print("Processing child of ", node)
			childReplacement = walkAST(node.child, funcToCall, node, shouldTrace)
			if childReplacement is not None:
				if childReplacement is not node.child:
					if _shouldTrace:
						print("Wrapped child replaced", node.child, "->", childReplacement, node, parent)
					node.child = childReplacement
			else:
				if _shouldTrace:
					print("Empty wrapper deleted", node, parent)
				return None
	else:
		if isinstance(node, (Wrapper, Iterable)):
			if _shouldTrace:
				print("NOT Processing children of ", node, "since `shouldDeepen` is ", shouldDeepen)
	return node


def rewriteReferences(node: Node, nameRemap: typing.Union[typing.Callable, typing.Mapping[str, str]]) -> None:
	"""Replaces references to a (non-)terminal with references to another (non-)terminal according to `nameRemap`"""
	if isinstance(nameRemap, Mapping):

		def nameRemap1(nodeName):
			return nameRemap.get(nodeName, None)

	else:
		nameRemap1 = nameRemap

	def cb(node: Node, parent: typing.Optional[Node]) -> bool:
		if isinstance(node, Ref):
			newName = nameRemap1(node.name)
			if newName is not None:
				node.name = newName
		return True, node, False

	walkAST(node, cb)


def getReferenced(node: Node, accumulator: set = None) -> typing.Set[str]:
	"""Get all the referenced names"""
	if accumulator is None:
		accumulator = set()

	def cb(node: Node, parent: typing.Optional[Node]) -> bool:
		if isinstance(node, Ref):
			accumulator.add(node.name)
		return True, node, False

	walkAST(node, cb)
	return accumulator


def getNames(node: Grammar, accumulator: dict = None) -> typing.Mapping[str, typing.Tuple[Node, Node]]:
	"""Return `Name` nodes children and parents, that must be sections in a valid UniGrammar file"""
	if accumulator is None:
		accumulator = {}

	def cb(node: Node, parent: typing.Optional[Node]) -> bool:
		if isinstance(node, Name):
			accumulator[node.name] = (node.child, parent)
			return False, node, False
		return True, node, False

	walkAST(node, cb)
	return accumulator
