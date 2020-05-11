import ast
import sys
import typing
from warnings import warn

from ..ast.base import Name, Ref, Wrapper
from ..ast.prods import Cap, Prefer, UnCap
from ..ast.templates import TemplateInstantiation
from ..ast.tokens import Opt, Seq
from .basicBlocks import genAssignStraight, genConstructAstObj, genFieldClass, isReturnTypeOptional, unifiedGetAttr
from .primitiveBlocks import astSelfArg
from .primitiveSpecificBlocks import IParseResultAST
from .specificBlocks import genIcecreamCall, genProcessorFuncCallForARef, getProcessorFuncNameForARef, getReturnTypeForANode, getReturnTypeForARef
from .WrapperFuncGen import WrapperFuncGen
from .WrapperGenContext import WrapperGenContext

WrapperGen = None  # initialized in __init__


class NotImplementedWrapperFuncGen(WrapperFuncGen):
	"""Wrapper function for these nodes is not needed."""

	__slots__ = ("name", "reason")

	def __init__(self, name: str = None, reason: str = None):
		self.name = name
		self.reason = reason

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.name) + (", " + repr(self.reason) if self.reason else "") + ")"

	def __call__(self, cls, obj: typing.Any, grammar: typing.Optional["Grammar"], ctx) -> typing.Any:
		raise NotImplementedError(repr(self) + ".__call__")

	def getType(self, nodeOrName: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		raise NotImplementedError(repr(self) + ".getType")

	def getFuncName(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None):
		raise NotImplementedError(repr(self) + ".getFuncName")


class NopWrapperFuncGen(WrapperFuncGen):
	"""Usually needed for modifiers not affecting AST"""

	__slots__ = ()

	def __call__(self, cls, obj: Wrapper, grammar: typing.Optional["Grammar"], ctx):
		return WrapperGen._processItem(obj.child, grammar, ctx)

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		return getReturnTypeForANode(node.child, ctx, refName)


class NameWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: Name, grammar: typing.Optional["Grammar"], ctx: None) -> str:
		return obj.name

	def getType(self, nodeOrName: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		raise NotImplementedError


class WrapperWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: Wrapper, grammar: typing.Optional["Grammar"], ctx):
		if isinstance(obj.child, Ref):
			processorFunc = getProcessorFuncNameForARef(obj.child.name, ctx)
			retType = getReturnTypeForARef(obj.child.name, ctx)
		else:
			raise NotImplementedError("For compatibility each stuff that is `iter`ed must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of `" + obj.name + "` into a separate rule")

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx, refName: str = None):
		return getReturnTypeForARef(node.child, ctx, refName)


class SeqWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: Seq, grammar: typing.Optional["Grammar"], ctx: WrapperGenContext) -> None:
		astObjClassName = ctx.currentProdName

		objName = "parsed"
		newOName = "rec"
		o = ast.Name(objName, ast.Load())

		body = []

		if ctx.shouldTrace(astObjClassName):
			body.append(genIcecreamCall(o))

		astObjClassNameAST, to, ctor = genConstructAstObj(newOName, astObjClassName)
		body.append(ctor)

		fields = []
		for f in obj.children:
			if isinstance(f, Cap):
				fields.append(f.name)
				chld = f.getASTVisibleChild()

				if isinstance(chld, Ref):
					nm = chld.name

					ctx.extendSchema(f.name, nm)
					fieldName = f.name

					retType = getReturnTypeForARef(nm, ctx)
					if isReturnTypeOptional(retType):
						arg = unifiedGetAttr(o, fieldName)
					else:
						arg = ast.Attribute(value=o, attr=fieldName, ctx=ast.Load())

					processorFuncCall = ast.Call(
						func=getProcessorFuncNameForARef(nm, ctx, None),
						args=[arg],
						keywords=[],
					)

					body.append(genAssignStraight(to=to, fieldName=fieldName, rhs=processorFuncCall, typ=retType))
				else:
					raise NotImplementedError("For compatibility each suff that is captured must be a `ref`. Otherwise we are unable to process these grammars uniformly for all the supported backends. Please put content of `" + f.name + "` into a separate rule")
			elif isinstance(f, UnCap):
				pass
			else:
				#raise ValueError("Item will be ignored when generating an AST", f)
				print("Item will be ignored when generating an AST:", f, file=sys.stderr)

		ctx.moduleMembers.append(genFieldClass(astObjClassName, fields, bases=(IParseResultAST,)))

		body.append(ast.Return(value=ast.Name(newOName, ast.Load())))

		ctx.members.append(
			ast.FunctionDef(
				name="process_" + astObjClassName,
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
				returns=astObjClassNameAST,
				type_comment=None,
			)
		)

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None) -> ast.Name:
		return ast.Name(refName, ast.Load())


class TemplateInstantiationWrapperFuncGen(WrapperFuncGen):
	__slots__ = ()

	def __call__(self, cls: typing.Type["WrapperGen"], obj: TemplateInstantiation, grammar: typing.Optional["Grammar"], ctx: WrapperGenContext) -> None:
		return ctx.members.extend(obj.template.transformWrapper(grammar, cls, ctx, **obj.params))

	def getType(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None) -> ast.Subscript:
		return node.template.getReturnType(ctx, **node.params)

	def getFuncName(self, node: typing.Union[Wrapper, Ref, str], ctx: WrapperGenContext, refName: str = None) -> ast.Attribute:
		return node.template.getProcFunc(ctx, **node.params)
