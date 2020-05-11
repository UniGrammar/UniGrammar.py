import ast
import inspect
import sys
import typing
from abc import ABC, ABCMeta, abstractmethod, abstractproperty

from ..ast import Grammar, Productions
from ..ast.base import Name, Node, Ref
from ..ast.prods import Cap
from ..ast.templates import TemplateInstantiation
from ..ast.tokens import Iter, Seq
from ..ast.transformations import walkAST
from ..WrapperGen.primitiveBlocks import ASTSelf

typingTypeMatchingMayBeBroken = typing.Type["str"] != typing.Type[str]


class _Template(ABC):
	__slots__ = ("id",)

	def __init__(self, iD: str, templatesRegistry: typing.Mapping[str, "_Template"]) -> None:
		self.id = iD
		templatesRegistry[iD] = self

	@abstractmethod
	def transformAST(self, grammar: Grammar, backend: "Generator", ctx: "GeneratorContext", parent: Name, **kwargs) -> typing.Tuple[Seq, Grammar]:
		raise NotImplementedError()

	@abstractmethod
	def transformWrapper(self, grammar: Grammar, backend: typing.Type["WrapperGen"], ctx: "WrapperGenContext", **kwargs) -> typing.Iterator[ast.AST]:
		raise NotImplementedError()

	def getProcFunc(self, ctx: "WrapperGenContext", **kwargs) -> ast.AST:
		return ast.Attribute(value=ASTSelf, attr=self.getProcFuncName(ctx, **kwargs), ctx=ast.Load())

	@abstractmethod
	def getProcFuncName(self, ctx: "WrapperGenContext", **kwargs) -> str:
		raise NotImplementedError()

	@abstractmethod
	def getReturnType(self, ctx: "WrapperGenContext", **kwargs) -> ast.Subscript:
		pass


trueSignatures = {
	k: inspect.signature(getattr(_Template, k)) for k in ("transformAST", "transformWrapper", "getProcFuncName", "getReturnType")
}


class TemplateMeta(ABCMeta):
	__slots__ = ()

	def __new__(cls: typing.Type["TemplateMeta"], className: str, parents: typing.Iterable[typing.Type], attrs: typing.Dict[str, typing.Any], *args, **kwargs) -> "Template":
		attrs = type(attrs)(attrs)

		schemas = {}

		for k, etalon in trueSignatures.items():
			if k in attrs:
				sig = inspect.signature(attrs[k])

				def r():
					raise Exception("`transformAST` has wrong signature (" + str(sig) + "), must begin from POSITIONAL_OR_KEYWORD non-kwargs of " + str(etalon))

				sigP = tuple(p for p in sig.parameters.values() if p.kind == inspect._ParameterKind.POSITIONAL_OR_KEYWORD or p.kind == inspect._ParameterKind.POSITIONAL_ONLY)
				sigEP = tuple(ep for ep in etalon.parameters.values() if ep.kind == inspect._ParameterKind.POSITIONAL_OR_KEYWORD or ep.kind == inspect._ParameterKind.POSITIONAL_ONLY)
				lEt = len(sigEP)

				if lEt > len(sigP):
					r()

				sigMustMatch = sigP[:lEt]

				for ep, p in zip(sigEP, sigMustMatch):
					if ep.kind == inspect._ParameterKind.POSITIONAL_OR_KEYWORD or ep.kind == inspect._ParameterKind.POSITIONAL_ONLY:
						if ep.name != p.name:
							r()
						if ep.annotation != p.annotation:
							if isinstance(p.annotation, type):
								if ep.annotation != p.annotation.__name__ and not (typingTypeMatchingMayBeBroken and p.annotation.__name__ == "Type"):
									print(ep.annotation, p.annotation)
									r()

				schemas[k] = sigP[lEt:]

		if schemas:
			missingSchemas = set(trueSignatures) - set(schemas)
			schemas = iter(schemas.items())

			if missingSchemas:
				prevName, prevSchema = parents[0], parents[0].paramsSchema
			else:
				prevName, prevSchema = next(schemas)

			for name, schema in schemas:
				if prevSchema != schema:
					raise Exception("Non-mandatory params have been redefined inconsistently", name, schema, prevName, prevSchema)
				prevName, prevSchema = name, schema

			attrs["paramsSchema"] = schema

		res = super().__new__(cls, className, parents, attrs, *args, **kwargs)
		return res


class Template(_Template, metaclass=TemplateMeta):  # pylint:disable=abstract-method
	"""A base class for templates specified in python"""

	__slots__ = ()


class UserTemplate(_Template):  # pylint:disable=abstract-method
	"""A class for templates specified inside of grammars"""

	__slots__ = ("paramsSchema",)

	def __init__(self, iD: str, templatesRegistry: typing.Mapping[str, "_Template"], paramsSchema):
		super().__init__(iD, templatesRegistry)
		self.paramsSchema = paramsSchema


def expandTemplates(grammar: Grammar, backend: "Backend", ctx: "GeneratorContext", node: Node) -> None:
	def cb(node: Node, parent: typing.Optional[Node]) -> bool:
		if isinstance(node, TemplateInstantiation):
			mainNode, newG = node.template.transformAST(grammar, backend, ctx, parent, **node.params)
			expandTemplates(newG, backend, ctx, newG)
			expandTemplates(grammar, backend, ctx, mainNode)
			grammar.embed(newG)
			return False, mainNode, False
		return True, node, False

	walkAST(node, cb)
