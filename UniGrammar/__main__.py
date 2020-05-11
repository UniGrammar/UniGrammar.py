"""This module defines the CLI"""
import re
import typing
import warnings
from collections import defaultdict
from pathlib import Path

from pantarei import chosenProgressReporter
from plumbum import cli
from UniGrammarRuntime.grammarClasses import GrammarClass
from UniGrammarRuntime.ParserBundle import InMemoryGrammarResources, ParserBundle
from UniGrammarRuntimeCore.PoolManager import PoolManager

from . import parseUniGrammarFile, saveTranspiled, transpile, transpileFilesForGenerators
from .core.backend.Generator import Generator
from .core.backend.Runner import NotYetImplementedRunner, Runner
from .core.WrapperGen import WrapperGen
from .tools.multilanguage.antlr4 import ANTLR
from .tools.multilanguage.CoCoR import CoCoR
from .tools.multilanguage.waxeye import Waxeye
from .tools.python.arpeggio import Arpeggio
from .tools.python.lark import Lark
from .tools.python.parglare import Parglare
from .tools.python.parsimonious import Parsimonious
from .tools.python.TatSu import TatSu
from .tools.regExps.python import PythonRegExp

backendz = (Parglare, ANTLR, Waxeye, TatSu, Parsimonious, Arpeggio, CoCoR, Lark, PythonRegExp)
backendsNames = {b.RUNNER.PARSER.META.product.name: b for b in backendz}


class selectors:
	"""Contains methods to retrieve backends matching some criteria. Each method corresponds to a criteria"""

	@staticmethod
	def name(name: str) -> typing.Iterable[Generator]:
		"""Selects a backend based on its name"""
		b = backendsNames.get(name, None)
		if b is None:
			raise KeyError(name, backendsNames)

		yield b

	@staticmethod
	def lang(lang: str) -> typing.Iterable[Generator]:
		"""Selects a backend based on languages supported by the backend"""
		for b in backendz:
			if lang in b.META.runtimeLib:
				yield b

	@staticmethod
	def cls(grammarClass: str) -> typing.Iterable[Generator]:
		"""Selects a backend based on classes of grammars that can be implemented using it."""
		grammarClass = GrammarClass.fromStr(grammarClass)
		for b in backendz:
			for gCl in b.META.grammarClasses:
				if grammarClass < gCl:
					yield b
					break


selectorRx = re.compile("^(?:(lang|cls):)(.+)$")


def parseToolsString(s: str) -> typing.Iterable[Generator]:
	"""Parses `backend string` specifying selection backends using some criteria, selects the backends based on it and yields them"""
	m = selectorRx.match(s)
	if m:
		selector = getattr(selectors, m.group(1))
		s = m.group(2)
	else:
		selector = selectors.name
	for n in s.split(","):
		yield from selector(n)


allToolsNames = frozenset(("all", "*"))


def _parseToolsStrings(s: str) -> typing.Iterable[Generator]:
	if s in allToolsNames:
		return backendz
	for bs in s.split(":"):
		return parseToolsString(bs)


def parseToolsStrings(s: str) -> typing.Set[Generator]:
	"""Parses `backend string`s specifying selection backends using some criteria, selects the backends based on them and returns them. The set of backends is deduplicated."""
	return set(_parseToolsStrings(s))


class UniGrammarCLI(cli.Application):
	"""UniGrammar is a tool for transpiling grammars to other parsers generators."""


def createGeneratorsToToolsMapping(tools):
	generators = defaultdict(set)
	for t in tools:
		generators[t.GENERATOR].add(t)
	return dict(generators)


class UniGrammarCLICommandInvolvingTranspilation(cli.Application):
	"""A CLI command that requires transpilation of a grammar"""

	def prepare(self, tools, *files):  # pylint:disable=no-self-use
		"""Transpiles the files into in-memory grammar sources in the target DSLs ready to for further usage"""
		tools = parseToolsStrings(tools)
		generators = createGeneratorsToToolsMapping(tools)
		files = tuple(Path(file) for file in files)
		fileResMapping = dict(transpileFilesForGenerators(files, generators))
		return generators, fileResMapping, len(tools)


@UniGrammarCLI.subcommand("transpile")
class UniGrammarTranspileCLI(UniGrammarCLICommandInvolvingTranspilation):
	"""Transpile a unigrammar into a set of grammar files specific for parser generators."""

	def main(self, backends="all", *files: cli.ExistingFile):  # pylint:disable=keyword-arg-before-vararg,arguments-differ
		generatorsToTools, fileResMapping, toolsCount = self.prepare(backends, *files)
		saveTranspiled(fileResMapping, Path("."))


@UniGrammarCLI.subcommand("gen-bundle")
class UniGrammarGenBundleCLI(UniGrammarCLICommandInvolvingTranspilation):
	"""Generate a bundle containing almost everything needed for parsing."""

	# blacken = cli.Flag(["-B", "--no-black"], default=True, help="Do not postprocess the generated source with `black`")
	# autopep = cli.Flag(["-P", "--no-autopep8"], default=True, help="Do not postprocess the generated source with `autopep8`")
	outDir = cli.SwitchAttr(["-O", "--output-dir"], default="./parserBundle", help="The dir to which output parser bundle")
	trace = cli.Flag(["-t", "--trace"], default=False, help="Embed tracing code into wrapper")

	def main(self, backends="all", *files: cli.ExistingFile):  # pylint:disable=keyword-arg-before-vararg,arguments-differ
		outDir = Path(self.outDir).absolute()
		b = ParserBundle(outDir)

		generatorsToToolsMapping, transpiledFiles, toolsCount = self.prepare(backends, *files)

		for transpiled in transpiledFiles.values():
			for generator, transpiledResult in transpiled.backendResultMapping.items():
				for tool in generatorsToToolsMapping[generator]:
					if not issubclass(tool.RUNNER, NotYetImplementedRunner):
						runner = runnersPool(tool.RUNNER)
						compiler = parsersFactoriesAndCompilersPool(runner.COMPILER)
						compiled = compiler.compileStr(transpiledResult.text, "python")

						runner.saveCompiled(compiled, b.grammars[transpiledResult.id], generator.META)
					else:
						warnings.warn("Runner for " + repr(tool) + " is not yet implemented due to some reasons, you may want to compile manually")

		#b.initGenerators()

		with chosenProgressReporter(len(files), "compiling for backends") as pb:
			for f in files:
				f = Path(f)
				baseDir = f.absolute().parent

				pb.report(str(f), incr=0, op="generating wrapper")
				g = parseUniGrammarFile(f)
				sourceAST, caplessSchema, iterlessSchema = WrapperGen.transpile(g, trace=self.trace)

				thisR = b.grammars[g.meta.id]
				thisR.capSchema = caplessSchema
				thisR.iterSchema = sorted(iterlessSchema)
				thisR.wrapperAST = sourceAST

				#pb.report(str(f), incr=0, op="benchmarking")
				tests = tuple(g.tests.getTests(baseDir))
				if tests:
					sampleToBench = tests[-1]
					thisR.benchmarkAndUpdate(sampleToBench)
				else:
					warnings.warn("There are no tests, so the benchmark is skipped and the runtime will choose based on based on generic speed of parsers rather than on the speed of this concrete grammar in various parsers.")
				pb.report(str(f), incr=1)

		b.save()


def runTestsForGenerator(tests, runner, transpilationResult):
	"""Runs tests for a transpiled grammar using a specific runner (usually associated to a backend)."""
	compiler = parsersFactoriesAndCompilersPool(runner.COMPILER)
	parserFactory = parsersFactoriesAndCompilersPool(runner.PARSER)

	compiled = compiler.compileStr(transpilationResult.text, "python")
	parser = parserFactory.fromInternal(compiled)

	with chosenProgressReporter(len(tests), "testing") as pb:
		for i, test in enumerate(tests):
			try:
				parser(test)
				pb.report((test if len(test) < 10 else ("test " + str(i))))
			except BaseException as ex:  # pylint: disable=broad-except
				print(repr(test), file=pb)
				print(ex, file=pb)


runnersPool = PoolManager()
parsersFactoriesAndCompilersPool = PoolManager()


def runTests(generatorsToToolsMapping, fileResMapping, toolsCount):
	"""Runs tests for transpiled grammars."""
	print()

	for f, transpiled in fileResMapping.items():
		baseDir = f.absolute().parent

		results = transpiled.backendResultMapping
		with chosenProgressReporter(toolsCount, "testing grammars") as pb:
			for generator, transpilationResult in results.items():
				for tool in generatorsToToolsMapping[generator]:
					pb.report(tool.__name__, incr=0, op="testing")
					tests = tuple(transpiled.grammar.tests.getTests(baseDir))
					if tool.RUNNER is None:
						warnings.warn("Runner for " + repr(tool) + " is not yet implemented due to some reasons, you may want to compile manually")
						continue
					runner = runnersPool(tool.RUNNER)
					runTestsForGenerator(tests, runner, transpilationResult)
					pb.report(tool.__name__, incr=1, op="tested")


@UniGrammarCLI.subcommand("test")
class UniGrammarTestCLI(UniGrammarCLICommandInvolvingTranspilation):
	"""Transpile a specific unigrammar into a grammar and run tests on it"""

	def main(self, backends="all", *files: cli.ExistingFile):  # pylint:disable=keyword-arg-before-vararg,arguments-differ
		generatorsToToolsMapping, fileResMapping, toolsCount = self.prepare(backends, *files)
		runTests(generatorsToToolsMapping, fileResMapping, toolsCount)


@UniGrammarCLI.subcommand("vis")
class UniGrammarVisCLI(cli.Application):
	"""Visualizes the parse tree using the tools specific to the backend"""

	def main(self, backend: str, target: str, file: cli.ExistingFile, test: str):  # pylint:disable=keyword-arg-before-vararg,arguments-differ
		backends = parseToolsStrings(backend)
		if len(backends) != 1:
			raise ValueError("Only 1 backend is allowed here")
		backend = next(iter(backends))
		if backend.RUNNER is None:
			raise ValueError("Generator has no RUNNER", backend)

		file = Path(file)
		gr = parseUniGrammarFile(file)
		transpiledResult = transpile(gr, backend.GENERATOR)
		runner = runnersPool(backend.RUNNER)
		compiler = parsersFactoriesAndCompilersPool(runner.COMPILER)
		parserFactory = parsersFactoriesAndCompilersPool(runner.PARSER)
		compiled = compiler.compileStr(transpiledResult.text, target)
		parser = parserFactory.fromInternal(compiled)
		runner.visualize(parser, test)


@UniGrammarCLI.subcommand("lift")
class UniGrammarLiftCLI(cli.Application):
	"""Lifts a grammar from a tool-specific DSL into UniGrammar DSL"""

	def main(self, backend: str, file: cli.ExistingFile):
		from transformerz.serialization.yaml import yamlSerializer

		from . import transpile
		from .generators.UniGrammarDictGenerator import UniGrammarDictGenerator, transpileToSerialized

		backends = parseToolsStrings(backend)
		if len(backends) != 1:
			raise ValueError("Only 1 backend is allowed here")
		backend = next(iter(backends))
		if backend.LIFTER is None:
			raise ValueError("The backend has no LIFTER", backend)

		file = Path(file)
		lifter = backend.LIFTER()
		grammar = lifter(file.read_text())
		result = transpileToSerialized(grammar, UniGrammarDictGenerator, yamlSerializer)
		print(result)


if __name__ == "__main__":
	UniGrammarCLI.run()
