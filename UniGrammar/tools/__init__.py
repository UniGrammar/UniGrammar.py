"""
This dir and its subdirs contain some backends. A backend is a class organizing wrapping a third-party tool.
It consists of following components:
1. generator - generates the resulting tool-specific grammar. Should be placed into the dir `generators` if shared by multiple backends.
2. runner - wraps the tool itself to compile, debug and visualize grammars.
3. lifter - converts tool-specific DSL into UniGrammar DSL
"""
