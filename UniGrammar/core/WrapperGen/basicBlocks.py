import ast
import typing

from .primitiveBlocks import AST__slots__, ASTNone, ASTSelf, dirFunc, getAttrFunc, typingAST, typingIterableAST, typingOptionalAST, typingUnionAST
from .utils import makeTypeComment


def genTypingOptional(tp):
	return ast.Subscript(
		value=typingOptionalAST,
		slice=ast.Index(value=tp),
	)


def isSymbolMatchingTypingModule(node: ast.AST):
	return isinstance(node, typingAST.__class__) and node.id == typingAST.id


def isSymbolTypingModule(node: ast.AST):
	return node is typingAST or isSymbolMatchingTypingModule(node)


def isObjectMatchingTypingOptional(node: ast.AST):
	return isinstance(node, typingOptionalAST.__class__) and isSymbolTypingModule(node.value) and node.attr == typingOptionalAST.attr


def isObjectTypingOptional(node: ast.AST):
	return node is typingOptionalAST or isObjectMatchingTypingOptional(node)


def isReturnTypeOptional(node: ast.AST) -> bool:
	return isinstance(node, ast.Subscript) and isObjectTypingOptional(node.value)


def genTypingUnion(tps: typing.Union[ast.Subscript, ast.Name]) -> ast.Subscript:
	return ast.Subscript(
		value=typingUnionAST,
		slice=ast.Index(
			value=ast.Tuple(
				elts=list(tps),
			),
		),
	)


def genTypingIterable(tp: ast.Name) -> ast.Subscript:
	return ast.Subscript(
		value=typingIterableAST,
		slice=ast.Index(value=tp),
	)


def unifiedGetAttr(obj: ast.Name, propName: str) -> ast.Call:
	return ast.Call(func=getAttrFunc, args=[obj, ast.Str(propName), ASTNone], keywords=[])


def genDirCall(o: ast.Name) -> ast.Call:
	return ast.Call(func=dirFunc, args=[o], keywords=[])


def genPropGet(propName: str) -> ast.Attribute:
	return ast.Attribute(value=ASTSelf, attr=propName, ctx=ast.Load())


def genPropInit(name: str) -> ast.Assign:
	return ast.Assign(
		targets=[ast.Attribute(value=ASTSelf, attr=name, ctx=ast.Store())],
		value=ASTNone,
		type_comment=None,
	)


def gen__init__(fields: typing.Iterable[str]) -> ast.FunctionDef:
	return ast.FunctionDef(
		name="__init__",
		args=ast.arguments(
			posonlyargs=[],
			args=[ast.arg(arg="self", annotation=None, type_comment=None)],
			vararg=None,
			kwonlyargs=[],
			kw_defaults=[],
			kwarg=None,
			defaults=[],
		),
		body=[genPropInit(f) for f in fields],
		decorator_list=[],
		returns=None,
		type_comment=None,
	)


def genFieldClass(name: str, fields: typing.Iterable[str], bases=()) -> ast.ClassDef:
	"""Generates a struct-like class with __slots__"""

	return ast.ClassDef(
		name=name,
		bases=bases,
		keywords=[],
		body=[
			ast.Assign(
				targets=[AST__slots__],
				value=ast.Tuple(elts=[ast.Str(f) for f in fields], ctx=ast.Load()),
				type_comment=None,
			),
			gen__init__(fields),
		],
		decorator_list=[],
	)


def genConstructAstObj(varName: str, className: str, typ=None) -> typing.Tuple[ast.Name, ast.Name, ast.Assign]:
	"""
	Returns a tuple of 3 elements
	first is `className` AST node
	second is `varName` AST node
	third is `varName = className()`"""
	clsNameAST = ast.Name(id=className, ctx=ast.Load())
	return (
		clsNameAST,
		ast.Name(id=varName, ctx=ast.Load()),
		ast.Assign(
			targets=[ast.Name(id=varName, ctx=ast.Store())],
			value=ast.Call(func=clsNameAST, args=[], keywords=[]),
			type_comment=makeTypeComment(typ),
		),
	)


def genAssignStraight(to: ast.Name, fieldName: str, rhs: ast.AST, typ=None) -> ast.Assign:
	"""Returns `to.fieldName = <rhs>`"""

	return ast.Assign(
		targets=[ast.Attribute(value=to, attr=fieldName, ctx=ast.Store())],
		value=rhs,
		type_comment=makeTypeComment(typ),
	)


def genPythonSchemaDictASTAssignment(name: str, dic: typing.Dict):
	return ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=ast.parse(repr(dict(dic)), mode="eval"), type_comment=None)
