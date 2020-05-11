import ast
import typing

from transformerz.serialization.python import pythonASTSerializer


def makeModule(body: typing.List[ast.AST]) -> ast.Module:
	return ast.Module(body=body, type_ignores=[])


def makeTypeComment(node: typing.Optional[ast.AST]) -> typing.Optional[str]:
	if node is not None:
		return unparse(ast.Expression(node))


def unparse(node: ast.AST) -> str:
	assert isinstance(node, (ast.Module, ast.Expression))
	return pythonASTSerializer.unprocess(node)
