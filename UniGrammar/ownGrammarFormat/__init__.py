"""The code pasing `*.?ug` JSON-based files into grammars AST"""

import typing
from abc import ABC, abstractmethod
from ast import literal_eval
from pathlib import Path
from pprint import pprint
from warnings import warn

from ..core.ast import Characters, Comment, Fragmented, Grammar, GrammarMeta, Keywords, Productions, Spacer, Tokens
from ..core.ast.base import Name, Node, Ref
from ..core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars
from ..core.ast.prods import Cap, Prefer
from ..core.ast.tokens import Alt, Iter, Lit, Opt, Seq
from ..core.testing import AggregateTestingSpec, TestingSpec, TestingSpecLines, TestingSpecModel, testingSpecModelsSelector
from .decodeExtension import detectFormatFromFileExtension
from .sections import *

# the code is mostly self-documented here
# pylint: disable=missing-function-docstring


neutralGrammarNames = frozenset(("grammar",))


def deriveGrammarIdFromFilesNames(fileName: Path) -> str:
	s = fileName.stem
	if s in neutralGrammarNames:
		return fileName.parent.name
	return s


def parseUniGrammarFile(fileName: Path, grammarDefaultId: str = None) -> Grammar:
	underlyingParser, isBinary, isTest = detectFormatFromFileExtension(fileName.suffix)
	if isBinary:
		data = fileName.read_bytes()
	else:
		data = fileName.read_text(encoding="utf-8")

	# pylint: disable=no-else-return
	if not isTest:
		if grammarDefaultId is None:
			grammarDefaultId = deriveGrammarIdFromFilesNames(fileName)
		return parseUniGrammarData(data, underlyingParser, grammarDefaultId)
	else:
		return parseUniGrammarTestData(data, underlyingParser)


def parseUniGrammarData(data: [bytes, str], underlyingParser: typing.Callable, grammarDefaultId: str) -> Grammar:
	return parseUniGrammar(underlyingParser.process(data), grammarDefaultId)


def parseUniGrammarTestData(data: [bytes, str], underlyingParser: typing.Callable):
	raise NotImplementedError("Not yet implemented")


def parseUniGrammar(dic: typing.Mapping[str, typing.Any], grammarDefaultId: str = None) -> Grammar:
	meta = parseGrammarMeta(dic, grammarDefaultId)
	tests = parseGrammarTestsingSpecs(dic.get("tests", ()))
	chars = parseChars.parseSection(dic)
	keywords = parseKeywords.parseSection(dic)
	tokens = parseTokens.parseSection(dic)
	fragmented = parseFragmented.parseSection(dic)
	prods = parseProductions.parseSection(dic)
	return Grammar(meta=meta, tests=tests, chars=chars, keywords=keywords, tokens=tokens, fragmented=fragmented, prods=prods)


def parseTestingSpec(dic: typing.Mapping[str, typing.Any]) -> TestingSpecLines:
	model = dic["model"]
	if isinstance(model, str):
		model = TestingSpecModel[model]
	else:
		model = TestingSpecModel(model)
	files = dic["files"]
	return testingSpecModelsSelector[model](files)


def parseGrammarTestsingSpecs(tests: typing.Iterable[typing.Any]) -> TestingSpec:
	res = []
	for t in tests:
		res.append(parseTestingSpec(t))
	return AggregateTestingSpec(res)


def parseGrammarMeta(dic: typing.Mapping[str, typing.Any], grammarDefaultId: str = None) -> GrammarMeta:
	"""Parses and verifies grammar metadata"""
	meta = dic.get("meta", {})
	grammarId = meta.get("id", grammarDefaultId)
	if not isinstance(grammarId, str):
		raise ValueError("You must set an id and it must be a string, not ", grammarId)

	title = meta.get("title", None)
	if not isinstance(title, str):
		raise ValueError("`title` must be a string")

	license = meta.get("license", None)  # pylint:disable=redefined-builtin
	if not isinstance(license, str):
		warn("`license` should be set. Otherwise it is proprietary.")
		license = "proprietary"

	filenameRegExp = meta.get("filename-regexp", None)
	doc = dic.get("doc", None)

	if doc is None:
		warn("`doc` should be set.")

	docRef = dic.get("doc-ref", None)

	return GrammarMeta(iD=grammarId, title=title, licence=license, doc=doc, docRef=docRef, filenameRegExp=filenameRegExp)
