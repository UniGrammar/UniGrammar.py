import ast
import typing

from ..ast.base import Node
from ..CodeGen import CodeGenContext


class WrapperGenContext(CodeGenContext):
	__slots_ = ("moduleMembers", "members", "allBindings", "capToNameSchema", "itersProdNames", "trace")

	def __init__(self, currentProdName: typing.Optional[str], moduleMembers: typing.Iterable[typing.Union[ast.Import, ast.ImportFrom, ast.ClassDef]], members: typing.Iterable[ast.FunctionDef], allBindings: typing.Mapping[str, typing.Tuple[Node, Node]], capToNameSchema, itersProdNames, trace=None) -> None:
		super().__init__(currentProdName)
		self.moduleMembers = moduleMembers
		self.members = members
		self.allBindings = allBindings
		self.capToNameSchema = capToNameSchema
		self.itersProdNames = itersProdNames
		self.trace = trace

	def extendSchema(self, capName: str, refName: str, currentProdName: str = None):
		if currentProdName is None:
			currentProdName = self.currentProdName
		self.capToNameSchema[currentProdName][refName] = capName

	def shouldTrace(self, name: str) -> bool:
		if not isinstance(self.trace, set):
			return bool(self.trace)

		return name in self.trace
