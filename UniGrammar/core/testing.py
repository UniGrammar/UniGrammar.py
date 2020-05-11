import typing
from abc import ABC, abstractmethod
from enum import IntEnum
from pathlib import Path


class TestingSpecModel(IntEnum):
	file = 0
	lines = 1


class ITestingSpec(ABC):
	__slots__ = ()

	@abstractmethod
	def getTests(self, baseDir: Path):
		raise NotImplementedError()


class TestingSpec(ITestingSpec):  # pylint.disable=abstract-method
	__slots__ = ("files",)

	def __init__(self, files: typing.Iterable[str]) -> None:
		self.files = files

	def __repr__(self):
		return self.__class__.__name__ + "(" + ", ".join(repr(k) + "=" + repr(getattr(self, k)) for k in __class__.__slots__) + ")"  # pylint:disable=undefined-variable

	def getTestFiles(self, baseDir: Path) -> typing.Iterator[Path]:
		for testFileName in self.files:
			yield baseDir / testFileName


class AggregateTestingSpec(ITestingSpec):
	__slots__ = ("subspecs",)

	def __init__(self, subspecs: typing.Iterable[ITestingSpec]) -> None:
		self.subspecs = subspecs

	def getTests(self, baseDir: Path) -> None:
		for subSpec in self.subspecs:
			yield from subSpec.getTests(baseDir)


class TestingSpecFiles(TestingSpec):
	__slots__ = ()

	def getTests(self, baseDir: Path):
		for tF in self.getTestFiles(baseDir):
			yield tF.read_text(encoding="utf-8")


class TestingSpecLines(TestingSpec):
	__slots__ = ()

	def getTests(self, baseDir: Path) -> typing.Iterator[str]:
		for tF in self.getTestFiles(baseDir):
			with tF.open("rt", encoding="utf-8") as testStream:
				for line in testStream:
					if line[-1] == "\n":
						line = line[:-1]
						if line and line[-1] == "\r":
							line = line[:-1]
					if not line:
						continue
					yield line


testingSpecModelsSelector = {
	TestingSpecModel.file: TestingSpecFiles,
	TestingSpecModel.lines: TestingSpecLines,
}
