import ast

from ..defaults import mainParserVarName, mainProductionName, runtimeParserResultBaseName, runtimeWrapperInterfaceName
from .primitiveBlocks import ASTSelf

IWrapperAST = ast.Name(id=runtimeWrapperInterfaceName, ctx=ast.Load())
IParseResultAST = ast.Name(id=runtimeParserResultBaseName, ctx=ast.Load())
backendAST = ast.Attribute(value=ASTSelf, attr="backend", ctx=ast.Load())
walkStrategyAST = ast.Attribute(value=backendAST, attr="wstr", ctx=ast.Load())

mainProductionNameAttrAST = ast.Attribute(value=ASTSelf, attr=mainProductionName, ctx=ast.Load())
mainProductionNameNameAST = ast.Name(id=mainProductionName, ctx=ast.Store())
getSubTreeTextAST = ast.Attribute(value=backendAST, attr="getSubTreeText", ctx=ast.Load())
terminalNodeToStr = ast.Attribute(value=backendAST, attr="terminalNodeToStr", ctx=ast.Load())
backendParseAst = ast.Attribute(value=backendAST, attr="parse", ctx=ast.Load())
backendPreprocessASTAst = ast.Attribute(value=backendAST, attr="preprocessAST", ctx=ast.Load())
enterOptionalAst = ast.Attribute(value=backendAST, attr="enterOptional", ctx=ast.Load())

mainParserVarNameAST = ast.Name(id=mainParserVarName, ctx=ast.Store())

iterateCollectionAst = ast.Attribute(value=walkStrategyAST, attr="iterateCollection", ctx=ast.Load())
