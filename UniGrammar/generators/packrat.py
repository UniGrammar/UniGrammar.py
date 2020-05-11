import typing
from pathlib import Path

from UniGrammarRuntime.dslsMetadata import packrat as packratDSLMeta
from UniGrammarRuntime.ToolMetadata import Product
from UniGrammarRuntimeCore.ICompiler import DummyCompiler

from ..core.backend.Runner import Runner
from ..core.CharClassProcessor import CharClassMergeProcessor
from .pythonicGenerator import PythonicGenerator


class PackratGenerator(PythonicGenerator):
	META = packratDSLMeta

	assignmentOperator = " = "
	singleLineCommentStart = "#"
	alternativesSeparator = " / "

	DEFAULT_ORDER = ("prods", "fragmented", "keywords", "chars", "tokens")

	class CHAR_CLASS_PROCESSOR(CharClassMergeProcessor):
		charClassSetStart = '~r"' + PythonicGenerator.CHAR_CLASS_PROCESSOR.charClassSetStart
		charClassSetEnd = PythonicGenerator.CHAR_CLASS_PROCESSOR.charClassSetEnd + '"'

		@classmethod
		def encloseCharClass(cls, s: str, obj: "_CharClass", grammar: "Grammar") -> str:
			return super().encloseCharClass(s.replace('"', '\\"'), obj, grammar)
