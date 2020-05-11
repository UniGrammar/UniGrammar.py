import typing

from UniGrammarRuntime.backends.regExps.python import PythonRegExpParserFactory
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ....core.backend.Runner import Runner
from ....core.backend.Tool import Tool
from .generator import PythonRegExpGenerator
from .lifter import PythonRegExpLifter


class PythonRegExpRunner(Runner):
	__slots__ = ()

	COMPILER = DummyCompiler
	PARSER = PythonRegExpParserFactory

	def execute(self, g: typing.Any) -> typing.Any:
		return re.compile(g)

	def parse(self, parser: "_sre.SRE_Pattern", text: str) -> None:
		parser.exec(text)

	def trace(self, parser: "_sre.SRE_Pattern", text: str):
		raise NotImplementedError()

	def visualize(self, parser: "_sre.SRE_Pattern", text: str):
		raise NotImplementedError()


class PythonRegExp(Tool):
	RUNNER = PythonRegExpRunner
	GENERATOR = PythonRegExpGenerator
	LIFTER = PythonRegExpLifter
