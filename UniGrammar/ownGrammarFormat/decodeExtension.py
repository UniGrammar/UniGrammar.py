import typing

from transformerz.serialization.json import jsonSerializer

textExtMapping = {
	"j": jsonSerializer,
	"y": None,
	"p": None,
	"n": None,
	"h": None,
}


try:
	from transformerz.serialization.pon import ponSerializer

	textExtMapping["p"] = ponSerializer
except ImportError:
	pass

try:
	from transformerz.serialization.yaml import yamlSerializer

	textExtMapping["y"] = yamlSerializer
except ImportError:
	pass

try:
	from transformerz.serialization.neon import neonSerializer

	textExtMapping["n"] = neonSerializer
except ImportError:
	pass

try:
	from transformerz.serialization.hcl2 import hcl2Serializer

	textExtMapping["h"] = hcl2Serializer
except ImportError:
	pass


binaryExtMapping = {
	"c": None,
	"m": None,
	"p": None,
	#"o": None,
}

try:
	from transformerz.serialization.cbor import cborSerializer

	textExtMapping["c"] = cborSerializer
except ImportError:
	pass

try:
	from transformerz.serialization.msgpack import msgpackSerializer

	textExtMapping["m"] = msgpackSerializer
except ImportError:
	pass

try:
	from transformerz.serialization.plist import plistSerializer

	textExtMapping["p"] = plistSerializer
except ImportError:
	pass


extensionBasePostfix = "ug"
extensionBinaryPrefix = "b"
extensionTestPrefix = "t"


def detectFormatFromFileExtension(ext: str) -> typing.Tuple[typing.Callable, bool, bool]:
	ext = ext.lower()[1:]
	if len(ext) < 3 or ext[-2:] != extensionBasePostfix:
		raise ValueError("Wrong file extension")
	restSfx = ext[:-2]
	if restSfx[-1] == extensionTestPrefix:
		restSfx = restSfx[:-1]
		isTest = True
	else:
		isTest = False

	if restSfx[-1] == extensionBinaryPrefix:
		restSfx = restSfx[:-1]
		mapping = binaryExtMapping
		isBinary = True
	else:
		mapping = textExtMapping
		isBinary = False

	serializer = mapping[restSfx]

	if serializer is None:
		raise NotImplementedError("Transformer for the underlying format is not present on your machine.")

	return serializer, isBinary, isTest
