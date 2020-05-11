from .base import ASTNodeLayer, Name, Wrapper
from .tokens import Seq


class Prefer(Wrapper):
	"""A preferrence for parser generators that allow to set them. Some grammars for some parser generators are impossible without them."""

	NODE_LAYER = ASTNodeLayer.fragment
	AST_INVISIBLE = True

	__slots__ = ("preference",)

	def __init__(self, child: Seq, preference: str) -> None:
		super().__init__(child)
		self.preference = preference


class Cap(Name):
	"""A name of a capture."""

	NODE_LAYER = ASTNodeLayer.production

	__slots__ = ()


class UnCap(Wrapper):
	"""Marks items that don't go into AST."""

	NODE_LAYER = ASTNodeLayer.production
	STACK_INVISIBLE = True
	AST_INVISIBLE = True

	__slots__ = ()


class BackRef(Name):
	"""A name of an existing `Cap`ture that have been defined IN THE SAME `Seq` that must be literaly matched."""

	NODE_LAYER = ASTNodeLayer.production

	__slots__ = ()
