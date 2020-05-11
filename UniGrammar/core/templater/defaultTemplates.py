import typing

from ..ast import Grammar, Productions
from ..ast.base import Name, Node, Ref
from ..ast.prods import Cap
from ..ast.tokens import Iter, Seq
from ..backend.Generator import Generator, GeneratorContext
from ..WrapperGen import ASTSelf, WrapperGen, WrapperGenContext, ast, astSelfArg, getProcessorFuncNameForARef, getReturnTypeForARef
from ..WrapperGen.IterWrapperFuncGen import genIterateCollectionLoop, genProcessCollectionToList, genTypingIterable
from ..WrapperGen.specificBlocks import genProcessorFuncCallForARef
from . import Template


class Delimited(Template):
	"""This template defines a list of items with separators"""

	__slots__ = ()

	def genNames(self, itemsName: str, singleItemName: str = None) -> typing.Tuple[str, str, str, str, str]:
		if singleItemName is None:
			if itemsName[-1] != "s" and len(itemsName) > 2:
				raise ValueError("Name must end with `s` so we can remove the `s` and get single item name")

			singleItemName = itemsName[:-1]

		firstItemCapName = "first_" + singleItemName
		restItemCapName = "rest_" + singleItemName
		restItemWithDelimiterCapName = restItemCapName + "_with_del"
		restItemsWithDelimiterCapName = restItemCapName + "s_with_del"

		restItemsWithDelimiterProdName = restItemsWithDelimiterCapName + "F"
		restItemWithDelimiterProdName = restItemWithDelimiterCapName + "F"

		return restItemsWithDelimiterProdName, restItemWithDelimiterProdName, firstItemCapName, restItemCapName, restItemsWithDelimiterCapName

	def transformAST(self, grammar: Grammar, backend: Generator, ctx: GeneratorContext, parent: Name, part: Node, delimiter: Node, singleItemName: typing.Optional[str] = None) -> typing.Tuple[Seq, Grammar]:
		if not isinstance(parent, Name):
			raise ValueError("Parent of `" + self.id + "` template must be a `Name` node", parent)

		restItemsWithDelimiterProdName, restItemWithDelimiterProdName, firstItemCapName, restItemCapName, restItemsWithDelimiterCapName = self.genNames(parent.name, singleItemName)

		mainNode = Seq(
			Cap(firstItemCapName, part),
			Cap(restItemsWithDelimiterCapName, Ref(restItemsWithDelimiterProdName)),
		)

		newProds = Productions(
			[
				Name(
					restItemsWithDelimiterProdName,
					Iter(
						Ref(restItemWithDelimiterProdName),
						0,
					),
				),
				Name(
					restItemWithDelimiterProdName,
					Seq(
						delimiter,
						Cap(restItemCapName, part),
					),
				),
			]
		)
		return mainNode, Grammar(meta=None, prods=newProds)

	def getProcFuncName(self, ctx: WrapperGenContext, part: Node, delimiter: Node, singleItemName: typing.Optional[str] = None) -> str:
		return "process_delimited_" + part.name

	def getReturnType(self, ctx: WrapperGenContext, part: Node, delimiter: Node, singleItemName: typing.Optional[str] = None) -> ast.Subscript:
		return genTypingIterable(ast.Name(getReturnTypeForARef(part.name, ctx), ctx=ast.Load()))

	def transformWrapper(self, grammar: Grammar, backend: typing.Type[WrapperGen], ctx: WrapperGenContext, part: Node, delimiter: Node, singleItemName: typing.Optional[str] = None) -> typing.Iterator[ast.FunctionDef]:
		restItemsWithDelimiterProdName, restItemWithDelimiterProdName, firstItemCapName, restItemCapName, restItemsWithDelimiterCapName = self.genNames(ctx.currentProdName, singleItemName)

		iterVarName = "f"
		iterVarNode = ast.Name(id=iterVarName, ctx=ast.Load())

		if isinstance(part, Ref):
			processorFuncCall, processorFuncRetType = genProcessorFuncCallForARef(iterVarNode, part.name, ctx)
		else:
			raise NotImplementedError("For compatibility each suff that is `iter`ed must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of `part` into a separate rule")

		parentName = "rec"
		returnType = self.getReturnType(ctx, part, delimiter)

		funcName = self.getProcFuncName(ctx, part, delimiter)
		iterFuncName = funcName + "_"
		firstArgName = "parsed"

		ctx.extendSchema(firstItemCapName, part.name)
		ctx.extendSchema(restItemsWithDelimiterCapName, restItemsWithDelimiterProdName)
		ctx.extendSchema(restItemCapName, part.name, restItemWithDelimiterProdName)
		ctx.itersProdNames.add(restItemsWithDelimiterProdName)

		o = ast.Name(id=firstArgName, ctx=ast.Load())
		yield ast.FunctionDef(
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
				ast.Expr(
					value=ast.Yield(
						value=ast.Attribute(value=o, attr=firstItemCapName, ctx=ast.Load()),
					),
				),
				genIterateCollectionLoop(
					ast.Attribute(value=o, attr=restItemsWithDelimiterCapName, ctx=ast.Load()),
					iterVarName,
					ast.Attribute(
						value=iterVarNode,
						attr=restItemCapName,
						ctx=ast.Load(),
					),
				),
			],
			decorator_list=[],
			returns=returnType,
			type_comment=None,
		)
		yield from genProcessCollectionToList(funcName=funcName, parentName=parentName, iterFuncName=iterFuncName, processorFuncCall=processorFuncCall, iterVarNode=iterVarNode, returnType=processorFuncRetType)


defaultTemplatesRegistry = {}
Delimited("delimited", defaultTemplatesRegistry)
