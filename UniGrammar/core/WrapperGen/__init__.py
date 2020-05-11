import ast
import typing
from abc import ABC, abstractmethod
from collections import defaultdict

from ..ast import Characters, Fragmented, Grammar, Keywords, Section, Tokens
from ..ast.base import Name, Node, Ref, Wrapper
from ..ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ..ast.prods import Cap
from ..ast.templates import TemplateInstantiation
from ..ast.tokens import Alt, Iter, Lit, Opt, Seq
from ..ast.transformations import getNames
from ..CodeGen import CodeGen, CodeGenContext
from ..defaults import mainParserVarName, runtimeModuleName, runtimeParserResultBaseName, runtimeWrapperInterfaceModuleName, runtimeWrapperInterfaceName
from . import restWrapperFuncGens, specificBlocks
from .AltWrapperFuncGen import AltWrapperFuncGen, OptWrapperFuncGen
from .IterWrapperFuncGen import IterWrapperFuncGen
from .primitiveBlocks import ASTSelf, astSelfArg, emptySlots
from .primitiveSpecificBlocks import IWrapperAST, backendParseAst, backendPreprocessASTAst, mainParserVarNameAST, mainProductionNameNameAST
from .restWrapperFuncGens import NameWrapperFuncGen, NopWrapperFuncGen, NotImplementedWrapperFuncGen, SeqWrapperFuncGen, TemplateInstantiationWrapperFuncGen
from .specificBlocks import getProcessorFuncNameForARef, getReturnTypeForARef
from .utils import makeModule
from .WrapperGenContext import WrapperGenContext


def gen__call__(rootItemType: str, ctx: "WrapperGenContext", parsedName: str = "parsed") -> ast.FunctionDef:
	processorFunc = getProcessorFuncNameForARef(rootItemType, ctx)
	retType = getReturnTypeForARef(rootItemType, ctx)
	astVarLoad = ast.Name(id=parsedName, ctx=ast.Load())
	astVarStore = ast.Name(id=parsedName, ctx=ast.Store())
	return ast.FunctionDef(
		name="__call__",
		args=ast.arguments(
			posonlyargs=[],
			args=[
				astSelfArg,
				ast.arg(arg="s", annotation=ast.Name(id="str", ctx=ast.Load()), type_comment=None),
			],
			vararg=None,
			kwonlyargs=[],
			kw_defaults=[],
			kwarg=None,
			defaults=[],
		),
		body=[
			ast.Assign(
				targets=[astVarStore],
				value=ast.Call(func=backendParseAst, args=[ast.Name(id="s", ctx=ast.Load())], keywords=[]),
				type_comment=None,
			),
			ast.Assign(
				targets=[astVarStore],
				value=ast.Call(func=backendPreprocessASTAst, args=[astVarLoad], keywords=[]),
				type_comment=None,
			),
			ast.Return(
				value=ast.Call(
					func=processorFunc,
					args=[astVarLoad],
					keywords=[],
				)
			),
		],
		decorator_list=[],
		returns=retType,
		type_comment=None,
	)


def genParserClass(itemName: str, subItems: typing.Iterable[ast.FunctionDef]) -> ast.ClassDef:
	body = [emptySlots, *subItems]

	return ast.ClassDef(
		name=itemName + "Parser",
		bases=[IWrapperAST],
		keywords=[],
		body=body,
		decorator_list=[],
	)


class WrapperGen(CodeGen):
	__slots__ = ()

	Name = classmethod(NameWrapperFuncGen())
	Iter = classmethod(IterWrapperFuncGen())
	Alt = classmethod(AltWrapperFuncGen())
	Seq = classmethod(SeqWrapperFuncGen())
	Opt = classmethod(OptWrapperFuncGen())
	TemplateInstantiation = classmethod(TemplateInstantiationWrapperFuncGen())
	Prefer = classmethod(NopWrapperFuncGen())

	CharRange = classmethod(NotImplementedWrapperFuncGen("CharRange"))
	CharClassUnion = classmethod(NotImplementedWrapperFuncGen("CharClassUnion"))
	WellKnownChars = classmethod(NotImplementedWrapperFuncGen("WellKnownChars"))
	CharClass = classmethod(NotImplementedWrapperFuncGen("CharClass"))
	Cap = classmethod(NotImplementedWrapperFuncGen("Cap"))
	Lit = classmethod(NotImplementedWrapperFuncGen("Lit"))
	#Ref = classmethod(NotImplementedWrapperFuncGen("Ref"))

	@classmethod
	def transpile(cls, grammar: Grammar, trace=None) -> typing.Tuple[str, typing.Mapping]:
		return cls.embedGrammar(grammar, trace=trace)

	@classmethod
	def _processItem(cls, el, grammar, ctx):
		clsNm = type(el).__name__
		processor = getattr(cls, clsNm)
		return processor(el, grammar, ctx)

	@classmethod
	def genImports(cls, trace):
		yield ast.Import(names=[ast.alias(name="typing", asname=None)])
		if trace:
			yield ast.ImportFrom(
				module="icecream",
				names=[
					ast.alias(name="ic", asname=None),
				],
				level=0,
			)
		yield ast.ImportFrom(
			module=runtimeModuleName + "." + runtimeWrapperInterfaceModuleName,
			names=[
				ast.alias(name=runtimeWrapperInterfaceName, asname=None),
				ast.alias(name=runtimeParserResultBaseName, asname=None),
			],
			level=0,
		)

	@classmethod
	def embedGrammar(cls, grammar: Grammar, ctx: WrapperGenContext = None, trace=None) -> typing.Any:
		members = []
		moduleMembers = []
		moduleMembers.extend(cls.genImports(trace=trace))

		allBindings = getNames(grammar)
		capToNameSchema = defaultdict(dict)
		itersProdNames = set()

		for p in grammar.prods:
			if isinstance(p, Name):
				name = cls.Name(p, grammar, ctx=None)
				prod = p.child

				cls._processItem(prod, grammar, WrapperGenContext(name, moduleMembers, members, allBindings, capToNameSchema, itersProdNames, trace=trace))

		mainProduction = grammar.prods.findFirstRule()
		members.append(
			ast.Assign(
				targets=[mainProductionNameNameAST],
				value=ast.Name(id=getProcessorFuncNameForARef(mainProduction.name, WrapperGenContext(None, moduleMembers, members, allBindings, capToNameSchema, itersProdNames, trace=trace)).attr),  # pylint: disable=no-member
				type_comment=None,
			)
		)
		# members.append(gen__call__(mainProduction.name, WrapperGenContext(None, moduleMembers, members, allBindings, capToNameSchema, itersProdNames, trace=trace), parsedName="parsed"))
		# members.append(genPythonSchemaDictASTAssignment("__CAP_TO_NAME_SCHEMA_DICT__", capToNameSchema))
		mainParserClass = genParserClass(mainProduction.name, members)
		moduleMembers.append(mainParserClass)
		moduleMembers.append(
			ast.Assign(
				targets=[mainParserVarNameAST],
				value=ast.Name(mainParserClass.name, ctx=ast.Load()),  # pylint: disable=no-member
				type_comment=None,
			)
		)
		return makeModule(moduleMembers), capToNameSchema, itersProdNames


specificBlocks.WrapperGen = WrapperGen
restWrapperFuncGens.WrapperGen = WrapperGen
