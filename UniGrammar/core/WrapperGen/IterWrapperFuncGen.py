import ast
import typing

from ..ast.base import Ref, Wrapper
from ..ast.tokens import Iter
from .basicBlocks import genTypingIterable
from .primitiveBlocks import ASTSelf, astSelfArg
from .restWrapperFuncGens import WrapperWrapperFuncGen
from .specificBlocks import genIterateListCall, genProcessorFuncCallForARef, getReturnTypeForARef
from .WrapperGenContext import WrapperGenContext


def genIterateCollectionLoop(listVar: ast.Attribute, iterVarName: str, yieldBody: ast.Attribute) -> ast.For:
	res = ast.For(
		target=ast.Name(id=iterVarName, ctx=ast.Store()),
		iter=genIterateListCall(listVar),
		body=[
			ast.Expr(
				value=ast.Yield(
					value=yieldBody,
				),
			),
		],
		orelse=[],
		type_comment=None,
	)
	return res


def genProcessCollectionToList(funcName: str, parentName: str, iterFuncName: str, processorFuncCall: ast.Attribute, iterVarNode, firstArgName: str = "parsed", returnType: None = None) -> typing.Iterator[ast.FunctionDef]:
	"""Generates a function transforming a collection (`min`) or a macro around it into a python `list` of nodes"""

	o = ast.Name(id=firstArgName, ctx=ast.Load())
	yield ast.FunctionDef(
		name=funcName,
		args=ast.arguments(
			posonlyargs=[],
			args=[
				astSelfArg,
				ast.arg(arg=firstArgName, annotation=None, type_comment=None),
			],
			vararg=None,
			kwonlyargs=[],
			kw_defaults=[],
			kwarg=None,
			defaults=[],
		),
		body=[
			ast.Return(
				value=ast.ListComp(
					elt=processorFuncCall,
					generators=[
						ast.comprehension(target=iterVarNode, iter=ast.Call(func=ast.Attribute(value=ASTSelf, attr=iterFuncName, ctx=ast.Load()), args=[o], keywords=[]), ifs=[], is_async=0),
					],
				)
			)
		],
		decorator_list=[],
		returns=(genTypingIterable(returnType) if returnType else None),
		type_comment=None,
	)


def genProcessCollection(propName, processorFuncCall, returnType, iterVarNode, parentName="rec"):
	funcName = "process_" + propName
	iterFuncName = funcName + "_"
	firstArgName = "parsed"

	o = ast.Name(id=firstArgName, ctx=ast.Load())

	funcDef = ast.FunctionDef(
		name=iterFuncName,
		args=ast.arguments(
			posonlyargs=[],
			args=[astSelfArg, ast.arg(arg=firstArgName, annotation=None, type_comment=None)],
			vararg=None,
			kwonlyargs=[],
			kw_defaults=[],
			kwarg=None,
			defaults=[],
		),
		body=[
			genIterateCollectionLoop(
				o,
				iterVarNode.id,
				iterVarNode,
			),
		],
		decorator_list=[],
		returns=(genTypingIterable(returnType) if returnType else None),
		type_comment=None,
	)
	yield funcDef
	yield from genProcessCollectionToList(funcName=funcName, parentName=parentName, iterFuncName=iterFuncName, processorFuncCall=processorFuncCall, iterVarNode=iterVarNode, returnType=returnType)


class IterWrapperFuncGen(WrapperWrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: Iter, grammar: typing.Optional["Grammar"], ctx: WrapperGenContext):
		ctx.itersProdNames.add(ctx.currentProdName)
		if isinstance(obj.child, Ref):
			iterVarName = "f"
			iterVarNode = ast.Name(id=iterVarName, ctx=ast.Load())
			processorFuncCall, retType = genProcessorFuncCallForARef(iterVarNode, obj.child.name, ctx)
			ctx.members.extend(genProcessCollection(ctx.currentProdName, processorFuncCall, retType, iterVarNode))
		else:
			raise NotImplementedError("For compatibility each suff that is `iter`ed must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of `" + obj.name + "` into a separate rule")

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		return genTypingIterable(super().getType(node, ctx, refName))
