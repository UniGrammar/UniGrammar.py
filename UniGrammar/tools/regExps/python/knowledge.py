import sre_constants as sc

from ....core.ast.characters import CharClass, CharClassUnion, CharRange, WellKnownChars

removedOpcodes = [sc.MAX_REPEAT, sc.MIN_REPEAT]  # due to some reason in sre_constants these opcodes are removed from OPCODES.
fullOpcodes = sc.OPCODES + removedOpcodes
lastOpcode = max(fullOpcodes)
LITERAL_STR = sc._NamedIntConstant(lastOpcode + 1, "LITERAL_STR")
del lastOpcode
CAPTURE_GROUP = sc._NamedIntConstant(sc.OPCODES[-1] + 1, "CAPTURE_GROUP")

wellKnownRegExpRemap = {
	sc.CATEGORY_WORD: CharClassUnion(WellKnownChars("ascii_letters"), WellKnownChars("digits"), CharClass("_")),
	sc.CATEGORY_DIGIT: WellKnownChars("digits"),
	sc.CATEGORY_NOT_WORD: CharClassUnion(WellKnownChars("ascii_letters"), WellKnownChars("digits"), CharClass("_"), negative=True),
	sc.CATEGORY_NOT_DIGIT: WellKnownChars("digits", negative=True),
	sc.CATEGORY_SPACE: WellKnownChars("whitespace"),
	sc.CATEGORY_NOT_SPACE: WellKnownChars("whitespace", negative=True),
}
wellKnownRegExpInvRemapSingle = {
	v: k
	for k, v in wellKnownRegExpRemap.items()
	if isinstance(v, WellKnownChars)
}

anyChar = CharClass("", negative=True)
