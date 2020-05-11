__all__ = ("RefParser", "AltCharClassParser", "RangeCharClassParser", "LitCharClassParser", "WellKnownCharClassParser", "AltParser", "LitKeywordsParser", "SeqParser", "OptParser", "TemplateParser", "parseRef", "parseAltCharClass", "parseRangeCharClass", "parseLitCharClass", "parseWellKnownCharClass", "parseAlt", "parseLitKeywords", "parseSeq", "parseOpt", "parseUnCap", "parseTemplateInstantiation")

import inspect
import typing
from copy import deepcopy
from warnings import warn

from ...core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, Productions, Spacer, Tokens
from ...core.ast.base import Name, Node, Ref
from ...core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ...core.ast.prods import Cap, Prefer, UnCap
from ...core.ast.templates import TemplateInstantiation
from ...core.ast.tokens import Alt, Iter, Lit, Opt, Seq
from ...core.templater.defaultTemplates import defaultTemplatesRegistry
from ..core import IShittyParser, SectionRecordParser, SectionSubRecordSingleParamParser

parseChars = None  # set from sections


class RefParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Ref,)
	ATTR_NAME = "ref"

	def apply(self, param: str, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Ref:
		return self.NODE(param)


parseRef = RefParser()


class AltCharClassParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = CharClassUnion, CharClass
	ATTR_NAME = "alt"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> typing.Union[CharClassUnion, CharClass]:
		if isinstance(param, str):
			if len(param) == 1:
				warn("Record in `chars` must be a `lit` because it is a single char")
			else:
				return CharClass(param, False)
		elif isinstance(param, list):
			return CharClassUnion(*tuple(parseChars(r) for r in param), negative=False)
		raise ValueError(self.__class__.ATTR_NAME + " is not recognized: ", param)


parseAltCharClass = AltCharClassParser()


class RangeCharClassParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (CharRange,)
	ATTR_NAME = "range"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> CharRange:
		if isinstance(param, list) and len(param) == 2:
			return self.NODE.fromBounds(*param, False)
		raise ValueError("If you use a `" + self.__class__.ATTR_NAME + "`, it must be a list of 2 elements", param)


parseRangeCharClass = RangeCharClassParser()


class LitCharClassParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (CharClass,)
	ATTR_NAME = "lit"

	def apply(self, param: str, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> CharClass:
		if not isinstance(param, str):
			raise ValueError("`" + self.__class__.ATTR_NAME + "` must be a `str`", param)
		if len(param) != 1:
			raise ValueError("`" + self.__class__.ATTR_NAME + "` in `chars` must be exactly 1 char long (" + str(len(param)) + " encountered). For keywords use `keywords` section.", param)
		return self.NODE(param, False)


parseLitCharClass = LitCharClassParser()


class WellKnownCharClassParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (WellKnownChars,)
	ATTR_NAME = "wellknown"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> WellKnownChars:
		return self.NODE(param, False)


parseWellKnownCharClass = WellKnownCharClassParser()


class AltParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Alt,)
	ATTR_NAME = "alt"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Alt:
		if isinstance(param, list):
			if not param:
				raise ValueError("There are no alternatives, what do you want?")
			if len(param) == 1:
				raise ValueError("It is ONE alternative, don't use `" + self.__class__.ATTR_NAME + "` for it.")
			return self.NODE(*tuple(recordParser(sr) for sr in param))
		raise ValueError(self.__class__.ATTR_NAME + " is not recognized: ", param)


parseAlt = AltParser()


class LitKeywordsParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Lit,)
	ATTR_NAME = "lit"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Lit:
		if not isinstance(param, str):
			raise ValueError("`" + self.__class__.ATTR_NAME + "` must be a `str`, but `" + repr(type(param)) + "` is given")
		if len(param) < 2:
			raise ValueError("`" + self.__class__.ATTR_NAME + "` in `keywords` must be more than 1 char long. Otherwise they go to `char`s.")
		return self.NODE(param)


parseLitKeywords = LitKeywordsParser()


class SeqParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Seq,)
	ATTR_NAME = "seq"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Seq:
		if isinstance(param, list):
			if not param:
				raise ValueError("This is an empty `" + self.__class__.ATTR_NAME + "`, what do you want?")
			if len(param) == 1:
				raise ValueError("It is only ONE item in a `" + self.__class__.ATTR_NAME + "`, don't use `" + self.__class__.ATTR_NAME + "` for it.")
			return self.NODE(*tuple(recordParser(sr) for sr in param))
		raise ValueError(self.__class__.ATTR_NAME + " is not recognized: ", param)


parseSeq = SeqParser()


class OptParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (Opt,)
	ATTR_NAME = "opt"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Opt:
		return self.NODE(recordParser(param))


parseOpt = OptParser()


class UnCapParser(SectionSubRecordSingleParamParser):
	__slots__ = ()
	NODES = (UnCap,)
	ATTR_NAME = "uncap"

	def apply(self, param, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> Opt:
		return self.NODE(recordParser(param))


parseUnCap = UnCapParser()


class TemplateParser(SectionRecordParser):
	__slots__ = ()
	NODES = (TemplateInstantiation,)
	ATTR_NAME = "template"

	def __call__(self, rec: typing.Mapping[str, typing.Any], recordParser: IShittyParser) -> TemplateInstantiation:
		templateName = rec.get(self.__class__.ATTR_NAME, None)
		if templateName is not None:
			try:
				template = defaultTemplatesRegistry[templateName]
			except KeyError:
				raise KeyError("Template is not registered", templateName)

			params = {}

			for paramSpec in template.paramsSchema:
				if paramSpec.name in rec:
					v = rec[paramSpec.name]
					if paramSpec.annotation is Node:
						if isinstance(v, dict):
							v = recordParser(v)
						else:
							raise ValueError("Arg `" + paramSpec.name + "` of `" + templateName + "` must be of type " + repr(Node))

					params[paramSpec.name] = v
				else:
					if paramSpec.default is inspect._empty:
						raise KeyError("You must provide arg `" + "` for the template `" + templateName + "`")

			return TemplateInstantiation(template, params)

		return None


parseTemplateInstantiation = TemplateParser()
