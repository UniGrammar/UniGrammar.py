import ast
import typing

from ..ast.base import Ref, Wrapper
from ..ast.prods import Cap
from ..ast.tokens import Alt, Opt
from .basicBlocks import genDirCall, genPropGet, genTypingOptional, genTypingUnion, unifiedGetAttr
from .primitiveBlocks import ASTNone, ASTTypeError, astSelfArg
from .specificBlocks import genEnterOptionalCall, genProcessorFuncCallForARef, getProcessorFuncNameForARef, getReturnTypeForARef
from .WrapperFuncGen import WrapperFuncGen
from .WrapperGenContext import WrapperGenContext


def genAlternativeBranchAST(o: ast.Name, fe, processorFuncCallAST, fieldName: str, ctx: WrapperGenContext) -> typing.Iterator[typing.Union[ast.Assign, ast.If]]:
	yield ast.Assign(
		targets=[ast.Name(id=fieldName, ctx=ast.Store())],
		value=unifiedGetAttr(o, fieldName),
		type_comment=None,
	)
	yield ast.If(
		test=ast.Compare(left=fe, ops=[ast.IsNot()], comparators=[ASTNone]),
		body=[
			ast.Return(
				value=processorFuncCallAST,
			),
		],
		orelse=[],
	)


def genAlternative(o: ast.Name, alt: str, ctx: WrapperGenContext) -> typing.Union[typing.Iterator[typing.Union[ast.Assign, ast.If]], ast.AST]:
	"""
	returns tuple: collection if branch AST nodes to add, AST of return type
	"""

	fieldName = alt.name
	fe = ast.Name(id=fieldName, ctx=ast.Load())
	processorFuncCallAST, retType = genProcessorFuncCallForARef(fe, alt.child.name, ctx)

	return genAlternativeBranchAST(o, fe, processorFuncCallAST, fieldName, ctx), retType


def genNoAltMatchedRaise(o: ast.Name) -> ast.Raise:
	return ast.Raise(exc=ast.Call(func=ASTTypeError, args=[genDirCall(o)], keywords=[]), cause=None)


class AltWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: Alt, grammar: typing.Optional["Grammar"], ctx: WrapperGenContext) -> None:
		body = []
		objName = "parsed"
		o = ast.Name(id=objName, ctx=ast.Load())

		returnTypes = []

		objIsAlt = isinstance(obj, Alt)

		for alt in obj.children:
			if isinstance(alt, Cap):
				if isinstance(alt.child, Ref):
					ctx.extendSchema(alt.name, alt.child.name)
					alternativeNodes, retType = genAlternative(o, alt, ctx)
					body.extend(alternativeNodes)
					returnTypes.append(retType)
				else:
					raise NotImplementedError("For compatibility each suff that is `alt`ed must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of " + ("`" + alt.name if hasattr(alt, "name") else "the `opt` struct in `" + ctx.currentProdName) + "` into a separate rule")
			else:
				raise NotImplementedError("Each item of `" + repr(obj) + "` must be `cap`tured in order to allow detection of its presence.")

		body.append(genNoAltMatchedRaise(o))

		if returnTypes:
			ctx.members.append(
				ast.FunctionDef(
					name="process_" + ctx.currentProdName,
					args=ast.arguments(
						posonlyargs=[],
						args=[astSelfArg, ast.arg(arg=objName, annotation=None, type_comment=None)],
						vararg=None,
						kwonlyargs=[],
						kw_defaults=[],
						kwarg=None,
						defaults=[],
					),
					body=body,
					decorator_list=[],
					returns=genTypingUnion(returnTypes),
					type_comment=None,
				)
			)

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None) -> ast.Subscript:
		return genTypingUnion(getReturnTypeForARef(alt.child, ctx) for alt in node.children if isinstance(alt, Cap))


class OptWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls, obj: Opt, grammar: typing.Optional["Grammar"], ctx):
		body = []
		objName = "parsed"
		o = ast.Name(id=objName, ctx=ast.Load())

		returnTypes = []

		objIsAlt = isinstance(obj, Alt)

		if isinstance(obj.child, Ref):
			fe = ast.Name(id=objName, ctx=ast.Load())
			#processorFuncCallAST, retType = genProcessorFuncCallForARef(fe, obj.child.name, ctx)

			processorFuncName = getProcessorFuncNameForARef(obj.child.name, ctx)
			retType = getReturnTypeForARef(obj.child.name, ctx)

			"""
			body.append(
				ast.If(
					test=ast.Compare(left=fe, ops=[ast.IsNot()], comparators=[ASTNone]),
					body=[
						ast.Return(
							value=processorFuncCallAST
						)
					],
					orelse=[],
				)
			)
			"""

			body.append(
				ast.Return(
					value=genEnterOptionalCall(fe, processorFuncName),
				)
			)

			returnTypes.append(retType)
		else:
			raise NotImplementedError("For compatibility each suff that is `opt`ed must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of " + ("`" + obj.name if hasattr(obj, "name") else "the `opt` struct in `" + ctx.currentProdName) + "` into a separate rule")

		ctx.members.append(
			ast.FunctionDef(
				name="process_" + ctx.currentProdName,
				args=ast.arguments(
					posonlyargs=[],
					args=[astSelfArg, ast.arg(arg=objName, annotation=None, type_comment=None)],
					vararg=None,
					kwonlyargs=[],
					kw_defaults=[],
					kwarg=None,
					defaults=[],
				),
				body=body,
				decorator_list=[],
				returns=genTypingOptional(retType),
				type_comment=None,
			)
		)

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		return genTypingOptional(getReturnTypeForARef(node.child, ctx))
