UniGrammar.py [![Unlicensed work](https://raw.githubusercontent.com/unlicense/unlicense.org/master/static/favicon.png)](https://unlicense.org/)
=============
~~[wheel (GitLab)](https://gitlab.com/UniGrammar/UniGrammar.py/-/jobs/artifacts/master/raw/dist/UniGrammar-0.CI-py3-none-any.whl?job=build)~~
~~[wheel (GHA via `nightly.link`)](https://nightly.link/UniGrammar/UniGrammar.py/workflows/CI/master/UniGrammar-0.CI-py3-none-any.whl)~~
~~![GitLab Build Status](https://gitlab.com/UniGrammar/UniGrammar.py/badges/master/pipeline.svg)~~
~~![GitLab Coverage](https://gitlab.com/UniGrammar/UniGrammar.py/badges/master/coverage.svg)~~
~~[![GitHub Actions](https://github.com/UniGrammar/UniGrammar.py/workflows/CI/badge.svg)](https://github.com/UniGrammar/UniGrammar.py/actions/)~~
[![Libraries.io Status](https://img.shields.io/librariesio/github/UniGrammar/UniGrammar.py.svg)](https://libraries.io/github/UniGrammar/UniGrammar.py)
[![Code style: antiflash](https://img.shields.io/badge/code%20style-antiflash-FFF.svg)](https://codeberg.org/KOLANICH-tools/antiflash.py)

UniGrammar is a tool providing a unified [DSL](https://en.wikipedia.org/wiki/Domain-specific_language) for writing [grammars](https://en.wikipedia.org/wiki/Formal_grammar) for transpilation into grammar DSLs specific to other tools.

Why?
----

When you create a grammar you want to make it compatible to different parser generators because:

* it allows it to be reused;

* it allows you utilize debugging tools available only to some of them.

And it is possible since most of grammar DSLs implement [EBNF](https://en.wikipedia.org/wiki/EBNF).

How?
----
The general workflow is as follows (but feel fre to do as you feel convenient):
* Collect or craft samples of texts in the laguage you wanna parse. They should be convenient for testing. You usually need texts tsting each language feature separately, and then interactions between them. You either need a dir of them, if each text occupies multiple lines, or a file of them, if each text occupies a single line.
* Choose a parser generator **CONVENIENT** for you for implementing that grammar. The parser generator must have debugging tools sufficient for your task. It usually should be the most generic class, I mean GLR. You can downgrade the class later. For now your goal is to just develop the grammar, get familiar to it and make it work. I used [`parglare`](https://github.com/igordejanovic/parglare).
* Make sure the needed tools are installed:
    * `UniGrammar` itself
    * `UniGrammarRuntime`
    * parser generator you want to support.
    * `git`
    * GUI diff and merge tool supporting `git` repos, such as `TortoiseGitMerge`, `WinMerge` (for Windows only) or `meld`.
* Setup your working dir:
    * Clone `https://codeberg.org/UniGrammar/grammars` and read its `ReadMe`.
    * Find a dir in the repo matching the purpose of the language you want to parse. Create a subdir there for your language. `cd` into it.
* Develop and debug a grammar for the selected parser generator. Make it work. Use debug tools, such as tracers and AST visualizers to make sure it works as intended. Commit it.
* Make an initial port of your grammar to `UniGrammar`:
    * Translate it to `grammar.yug`. For now just copy ad then manually translate. In future automatic assistance can be developed.
    * Use `UniGrammar transpile <yug file> <backend name>` to transpile it into a grammar for the backend of your choice.
    * Compare the generated spec to the one you have originally crafted. Make minor insignificant changes to the both specs to make them byte-by-byte identical, keeping the original spec working.
* Set up testing:
    * register the tests in your `yug` file
    * run `UniGrammar test <yug file> <backend name>` and make sure all the tests pass. This tests mean only that a source is pased without an issue. If they don't pass, fix the grammar.
* Make compatibility to the rest of backends, downgrading grammar class step-by-step. Modify the `yug` file and test untill it works for a backend. Bring compatibility to all the backends.
* You get an universal grammar suitable for more than 1 backends. Now it's time for deployment and behavioral tests.
    * generate a bundle using `UniGrammar gen-bundle <yug file> <backend name>`
    * Import runtime `from UniGrammarRuntime.ParserBundle import ParserBundle`
    * `b = ParserBundle(Path("path/to/bundle"))`
    * `w = b["your_grammar_name"].getWrapper()`
    * `parseTree = w("text to parse")`

Guidelines
----------
* An `*.*ug` file is a machine readable and writeable universal grammar file. It is a tree of serialized objects like the ones that can be serialized into JSON. `ug` stands for UniGrammar. It is prepended by a letter:
    * `y` stands for YAML
    * `j` stands for JSON
    * `p` stands for PON - "Pyhon Object Notation" that can be parsed securely using `ast.literal_eval`
    * `*b` stands for `binary`. Prepended by a letter identifying a binary format.
        * `c` - cbor
        * `m` - msgpack
        * `o` - own format

* An `*.*ug` file consists of 4 sections, each of them is a `list` of records:
    * `characters` for definition of character classes. Needed because of CoCo/R.
    * `keywords` - put there whole words that are reserved. Anything that identical to these words will be recognized as these words tokens.
    * `tokens` - consist of groups of `characters`. Cannot group other tokens and productions.
    * `fragmented` and `productions` - are productions resolved via a state machine. They are mostly the same, but they have big semantic difference, related to wrapper generated from them:
        * `fragmented` are considered to be simple text strings. They should never `cap`. It is an artificial class to support scannerful LL parsers. Scannerful LL parsers work from character classes. They split text into tokens and assign a type to each token based on character classes used in it, then do productions, and they never backtrace and the tokenizer doesn't know the context. This means token character classes in general should never overlap, otherwise the tokens may be wrong. So to support "tokens" with overlapping char ranges one splits them into tokens of non-overlapping char ranges, and these "tokens" are not tokens anymore, but productions. But they still have meaning of tokens. This section is for such "tokens". The postprocessor (can be automatically generated) should join them back into strings. Also their internal structure may be optimized out, or the backends it makes sense.
        * `productions` - usual productions, that must always contain at least 1 `cap` (otherwise they belong to `fragmened`, if you get invalid python code, you probably have put something that must be in `fragmented` to `productions`), defining named refs to parse tree children subnodes.

* use `id: <id>` to assign an id to each rule. It must he done for rules in sections.
* use `ref: <assigned id>` to refer an already created rule.
* use `alt: […]` to specify alternatives. **Works for all the sections.** For `chars` allows to enumerate characters.
* use `range: ['<start>', '<stop>']` to create a character range. `[<start>-<stop>]` in regexp syntax.
* use `wellknown: <name>` to specify a group of characters with a well-known name.
* use `neg: true` if the chars are to be excluded.
* use `lit: ...` to add a literal or a single character.
* use `min` to mark iteration. `min: 0` is transpiled to `…*` (`{…}`), `min: 1` is transpiled to `…+` (`… {…}`) in parglare (EBNF) syntaxes.
* use `opt` to mark optionality. It is transpiled to `…?` (`[…]`).
* use `seq: […]` to create a sequence.
* use `cap: <name>` to put the contents of this rule into the parse tree, if it is constructed.
* use `prefer: shift | reduce` to set a preferrence for `parglare`.
* use `spacer: <n>` to add `n` empty lines.

* use `name` in the root to specify a grammar name.

Here is an example: https://codeberg.org/KOLANICH-libs/AptSourcesList.py/blob/master/grammar.yug

Implemented backends
--------------------
In the order of decreasing performance:
* [parsimonious](https://github.com/erikrose/parsimonious)
* [waxeye](https://github.com/waxeye-org/waxeye) (PEG)
* [ANTLR 4](https://github.com/antlr/antlr4) (LL(*))
* [parglare](https://github.com/igordejanovic/parglare) (LR, GLR)
* [TatSu](https://github.com/neogeny/TatSu)


Not fully implemented backends
-------------------------------
* [CoCo/R](https://github.com/armornick/CocoR) and [CocoPy](https://codeberg.org/UniGrammar/CoCoPy) (LL(1))


Dependencies
------------
* [`rangeslicetools`](https://codeberg.org/KOLANICH-libs/rangeslicetools.py) - for computations with chars ranges
* [`plumbum`](https://github.com/tomerfiliba/plumbum) - for CLI
