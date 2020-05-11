"""UniGrammar is a tool and a lib to deal with parser generators uniformly"""

import typing
import warnings
from copy import deepcopy
from pathlib import Path

from .core.ast import Grammar
from .core.backend.Generator import Generator, TranspiledResult
from .ownGrammarFormat import parseUniGrammarFile


class GrammarTranspilationResults:  # pylint: disable=too-few-public-methods
	"""Represents transpilation results of an unigrammar: mainly a transpiled grammar"""

	__slots__ = ("grammar", "backendResultMapping")

	def __init__(self, grammar: Grammar, backendResultMapping: typing.Dict[typing.Any, TranspiledResult]) -> None:
		self.grammar = grammar
		self.backendResultMapping = backendResultMapping


def transpile(grammar: Grammar, backend: Generator) -> str:
	"""Transpiles a unigrammar into backend-specific grammar"""
	ctx = backend.initContext(grammar)
	backend.preprocessGrammar(grammar, ctx)
	lines = backend._transpile(grammar, ctx)

	return TranspiledResult(grammar.meta.id, "\n".join(lines))


def _transpileGrammarForGenerators(gr: Grammar, backends: typing.Iterable[Generator]) -> typing.Iterator[typing.Tuple[Generator, TranspiledResult]]:
	for backend in backends:
		yield backend, transpile(deepcopy(gr), backend)  # during transpilation AST is modified, so we need a fresh copy


def transpileGrammarForGenerators(gr: Grammar, backends: typing.Iterable[Generator]) -> GrammarTranspilationResults:
	"""Just transpiles a unigrammar for multiple backends"""
	return GrammarTranspilationResults(gr, dict(_transpileGrammarForGenerators(gr, backends)))


def transpileFileForGenerators(grammarFile: Path, backends: typing.Iterable[Generator]) -> GrammarTranspilationResults:
	"""Just transpiles a unigrammar for multiple backends"""
	gr = parseUniGrammarFile(grammarFile)  # during transpilation AST is modified, so we need a fresh copy
	return transpileGrammarForGenerators(gr, backends)


def transpileFilesForGenerators(files: typing.Iterable[Path], backends: typing.Iterable[Generator]) -> typing.Iterable[typing.Tuple[Path, GrammarTranspilationResults]]:
	"""Just transpiles multiple unigrammar files for multiple backends"""
	for file in files:
		yield file, transpileFileForGenerators(file, backends)


def saveTranspiled(transpiledFiles: typing.Dict[Path, GrammarTranspilationResults], outputDir: Path) -> None:
	"""Saves transpiled grammars (retured by `transpileFilesForGenerators` into files"""
	for transpiled in transpiledFiles.values():
		for backend, transpiledResult in transpiled.backendResultMapping.items():
			(outputDir / (transpiledResult.id + "." + backend.META.mainExtension)).write_text(transpiledResult.text, encoding="utf-8")
