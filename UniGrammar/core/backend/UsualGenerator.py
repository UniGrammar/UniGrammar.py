import typing

from ..ast import Grammar, MultiLineComment
from ..ast.characters import CharClass, CharClassUnion, WellKnownChars
from ..CharClassProcessor import CharClassMergeProcessor
from .Generator import Generator


class UsualGenerator(Generator):
	__slots__ = ()
	assignmentOperator = None
	capturingOperator = None
	endStatementOperator = None
	singleLineCommentStart = None
	multiLineCommentStart = None
	multiLineCommentEnd = None
	alternativesSeparator = " | "
	CHAR_CLASS_PROCESSOR = CharClassMergeProcessor  # : CharClassProcessor

	@classmethod
	def _wrapAlts(cls, alts: typing.Iterable[str], grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.alternativesSeparator.join(alts)

	@classmethod
	def wrapZeroOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return res + "*"

	@classmethod
	def wrapOneOrMore(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return res + "+"

	@classmethod
	def wrapZeroOrOne(cls, res: str, grammar: Grammar, ctx: typing.Any = None) -> str:
		return res + "?"

	@classmethod
	def _Name(cls, k: str, v: str, ctx: typing.Any = None) -> str:
		return k + cls.assignmentOperator + v + cls.endStatementOperator

	@classmethod
	def _Cap(cls, k: str, v: str) -> str:
		if cls.capturingOperator is not None:
			return k + cls.capturingOperator + v
		return v

	@classmethod
	def _Comment(cls, comment: str) -> str:
		return cls.singleLineCommentStart + comment

	@classmethod
	def MultiLineComment(cls, obj: MultiLineComment, grammar: Grammar, ctx: typing.Any = None) -> str:
		if cls.multiLineCommentStart is not None:
			return cls.multiLineCommentStart + "\n" + "\n".join(line for line in obj.value) + "\n" + cls.multiLineCommentEnd
		return super(__class__, cls).MultiLineComment(obj, grammar)  # pylint:disable=undefined-variable

	@classmethod
	def _escapeCharClassString(cls, s: str) -> typing.Iterable[str]:
		for c in s:
			yield cls.charClassEscaper(c)

	@classmethod
	def escapeCharClassString(cls, s: str) -> str:
		return "".join(cls._escapeCharClassString(s))

	@classmethod
	def CharClass(cls, obj: CharClass, grammar: Grammar, ctx: typing.Any = None) -> str:
		if len(obj.chars) == 1:
			return cls.wrapLiteralChar(obj.chars)
		return cls.CHAR_CLASS_PROCESSOR.wrapCharClass(cls, cls.escapeCharClassString(obj.chars), obj, grammar)

	@classmethod
	def WellKnownChars(cls, obj: WellKnownChars, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.resolve(obj.child, grammar)

	@classmethod
	def CharClassUnion(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.CHAR_CLASS_PROCESSOR.union(cls, obj, grammar)

	@classmethod
	def CharRange(cls, obj: CharClassUnion, grammar: Grammar, ctx: typing.Any = None) -> str:
		return cls.CHAR_CLASS_PROCESSOR.range(cls, obj, grammar)
