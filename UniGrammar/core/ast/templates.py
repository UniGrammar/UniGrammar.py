import typing

from .base import ASTNodeLayer, Node, Ref


class TemplateInstantiation(Node):
	__slots__ = ("template", "params")

	NODE_LAYER = ASTNodeLayer.any

	def __init__(self, template: "Template", params: typing.Dict[str, Ref]) -> None:
		super().__init__()
		self.template = template
		self.params = params
