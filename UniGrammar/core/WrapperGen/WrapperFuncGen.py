import ast
import typing
from abc import ABC, abstractmethod

from ..ast.base import Ref, Wrapper
from .primitiveBlocks import ASTSelf
from .WrapperGenContext import WrapperGenContext


class WrapperFuncGen(ABC):
	"""Stores the info needed to generate a wrapper function and its callers. Used to generate the function. Use with `classmethod`!"""

	__slots__ = ()

	@abstractmethod
	def __call__(self, cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx) -> typing.Any:
		"""Generates a wrapper function for an AST node type."""
		raise NotImplementedError

	@abstractmethod
	def getType(self, nodeOrName: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		"""Returns a return type of a wrapper function. Needed for proper typing."""
		raise NotImplementedError

	def getFuncName(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None) -> ast.Attribute:
		"""Generates wrapper function name"""
		return ast.Attribute(value=ASTSelf, attr="process_" + refName, ctx=ast.Load())
