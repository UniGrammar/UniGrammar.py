import ast

ASTNone = ast.NameConstant(value=None)
dirFunc = ast.Name(id="dir", ctx=ast.Load())
strAST = ast.Name(id="str", ctx=ast.Load())
getAttrFunc = ast.Name(id="getattr", ctx=ast.Load())

ASTSelf = ast.Name(id="self", ctx=ast.Load())
astSelfArg = ast.arg(arg="self", annotation=None, type_comment=None)
ASTSelfClass = ast.Attribute(value=ASTSelf, attr="__class__", ctx=ast.Load())
AST__slots__ = ast.Name(id="__slots__", ctx=ast.Load())
emptySlots = ast.Assign(targets=[ast.Name(id="__slots__", ctx=ast.Store())], value=ast.Tuple(elts=[], ctx=ast.Load()), type_comment=None)
ASTTypeError = ast.Name(id="TypeError", ctx=ast.Load())
typingAST = ast.Name(id="typing", ctx=ast.Load())
typingOptionalAST = ast.Attribute(value=typingAST, attr="Optional")
typingIterableAST = ast.Attribute(value=typingAST, attr="Iterable")
typingUnionAST = ast.Attribute(value=typingAST, attr="Union")
