"""Generate Python parser artifacts from the vendored Dart grammar."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "build" / "tools"
GRAMMAR_SOURCE = ROOT / "resources" / "grammars" / "dart3" / "Dart.g"
TRANSFORMED_GRAMMAR = Path("/tmp/Dart.g4")
OUTPUT_DIR = ROOT / "src" / "darta" / "infrastructure" / "antlr" / "generated" / "dart3"
ANTLR_VERSION = "4.13.2"
ANTLR_JAR = TOOLS_DIR / f"antlr-{ANTLR_VERSION}-complete.jar"
ANTLR_JAR_URL = f"https://www.antlr.org/download/antlr-{ANTLR_VERSION}-complete.jar"


def main() -> None:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _ensure_grammar_exists()
    _ensure_antlr_jar_exists()
    _transform_grammar()
    _generate_parser()
    _ensure_package_files()


def _ensure_grammar_exists() -> None:
    if not GRAMMAR_SOURCE.exists():
        raise SystemExit(f"missing grammar file: {GRAMMAR_SOURCE}")


def _ensure_antlr_jar_exists() -> None:
    if ANTLR_JAR.exists():
        return
    print(f"Downloading ANTLR {ANTLR_VERSION}...")
    urlretrieve(ANTLR_JAR_URL, ANTLR_JAR)


def _transform_grammar() -> None:
    text = GRAMMAR_SOURCE.read_text(encoding="utf-8")

    # a. Remove Java header imports
    text = text.replace(
        "@parser::header{\nimport java.util.Stack;\n}",
        "",
    )
    text = text.replace(
        "@lexer::header{\nimport java.util.Stack;\n}",
        "",
    )

    # b. Replace @parser::members { ... } block
    text = _replace_block(
        text,
        "@parser::members {",
        """\
@parser::members {
def _ensure_async_stack(self):
    if not hasattr(self, '_asyncEtcAreKeywords'):
        self._asyncEtcAreKeywords = [False]
def startAsyncFunction(self):
    self._ensure_async_stack(); self._asyncEtcAreKeywords.append(True)
def startNonAsyncFunction(self):
    self._ensure_async_stack(); self._asyncEtcAreKeywords.append(False)
def endFunction(self):
    self._ensure_async_stack()
    if self._asyncEtcAreKeywords:
        self._asyncEtcAreKeywords.pop()
def asyncEtcPredicate(self, tokenId):
    self._ensure_async_stack()
    if tokenId in (self.AWAIT, self.YIELD):
        return not self._asyncEtcAreKeywords[-1]
    return False
}""",
    )

    # c. Replace @lexer::members{ ... } block
    text = _replace_block(
        text,
        "@lexer::members{",
        """\
@lexer::members{
BRACE_NORMAL = 1
BRACE_SINGLE = 2
BRACE_DOUBLE = 3
BRACE_THREE_SINGLE = 4
BRACE_THREE_DOUBLE = 5
def _ensure_brace_stack(self):
    if not hasattr(self, '_braceLevels'):
        self._braceLevels = []
def currentBraceLevel(self, braceLevel):
    self._ensure_brace_stack()
    if not self._braceLevels: return False
    return self._braceLevels[-1] == braceLevel
def enterBrace(self): self._ensure_brace_stack(); self._braceLevels.append(1)
def enterBraceSingleQuote(self): self._ensure_brace_stack(); self._braceLevels.append(2)
def enterBraceDoubleQuote(self): self._ensure_brace_stack(); self._braceLevels.append(3)
def enterBraceThreeSingleQuotes(self): self._ensure_brace_stack(); self._braceLevels.append(4)
def enterBraceThreeDoubleQuotes(self): self._ensure_brace_stack(); self._braceLevels.append(5)
def exitBrace(self):
    self._ensure_brace_stack()
    if self._braceLevels: self._braceLevels.pop()
}""",
    )

    # d. Convert embedded parser actions (no spaces inside braces to avoid
    #    indentation errors in ANTLR-generated Python code)
    text = text.replace("{ startNonAsyncFunction(); }", "{self.startNonAsyncFunction()}")
    text = text.replace("{ startAsyncFunction(); }", "{self.startAsyncFunction()}")
    text = text.replace("{ endFunction(); }", "{self.endFunction()}")

    # e. Convert parser semantic predicate
    text = text.replace(
        "{ asyncEtcPredicate(getCurrentToken().getType()) }?",
        "{self.asyncEtcPredicate(self.getCurrentToken().type)}?",
    )

    # f. Convert embedded lexer actions
    text = text.replace("{ enterBrace(); }", "{self.enterBrace()}")
    text = text.replace("{ enterBraceSingleQuote(); }", "{self.enterBraceSingleQuote()}")
    text = text.replace("{ enterBraceDoubleQuote(); }", "{self.enterBraceDoubleQuote()}")
    text = text.replace("{ enterBraceThreeSingleQuotes(); }", "{self.enterBraceThreeSingleQuotes()}")
    text = text.replace("{ enterBraceThreeDoubleQuotes(); }", "{self.enterBraceThreeDoubleQuotes()}")
    text = text.replace("{ exitBrace(); }", "{self.exitBrace()}")
    text = text.replace("{ skip(); }", "{self.skip()}")

    # g. Convert lexer semantic predicates
    text = text.replace(
        "{ currentBraceLevel(BRACE_NORMAL) }?",
        "{self.currentBraceLevel(self.BRACE_NORMAL)}?",
    )
    text = text.replace(
        "{ currentBraceLevel(BRACE_SINGLE) }?",
        "{self.currentBraceLevel(self.BRACE_SINGLE)}?",
    )
    text = text.replace(
        "{ currentBraceLevel(BRACE_DOUBLE) }?",
        "{self.currentBraceLevel(self.BRACE_DOUBLE)}?",
    )
    text = text.replace(
        "{ currentBraceLevel(BRACE_THREE_SINGLE) }?",
        "{self.currentBraceLevel(self.BRACE_THREE_SINGLE)}?",
    )
    text = text.replace(
        "{ currentBraceLevel(BRACE_THREE_DOUBLE) }?",
        "{self.currentBraceLevel(self.BRACE_THREE_DOUBLE)}?",
    )

    TRANSFORMED_GRAMMAR.write_text(text, encoding="utf-8")
    print(f"Transformed grammar written to {TRANSFORMED_GRAMMAR}")


def _replace_block(text: str, header: str, replacement: str) -> str:
    """Replace a block that starts with `header` and ends at the first `}` on its own line."""
    start = text.find(header)
    if start == -1:
        raise SystemExit(f"Could not find block starting with: {header!r}")
    # Find the closing `}` on its own line after the header
    search_from = start + len(header)
    # Match a `}` that appears at the start of a line (optionally preceded by whitespace)
    match = re.search(r"^\}", text[search_from:], re.MULTILINE)
    if match is None:
        raise SystemExit(f"Could not find closing `}}` for block starting with: {header!r}")
    end = search_from + match.end()
    return text[:start] + replacement + text[end:]


def _generate_parser() -> None:
    command = [
        "java",
        "-jar",
        str(ANTLR_JAR),
        "-Dlanguage=Python3",
        "-visitor",
        "-no-listener",
        "-o",
        str(OUTPUT_DIR),
        str(TRANSFORMED_GRAMMAR),
    ]
    subprocess.run(command, check=True, cwd=ROOT)


def _ensure_package_files() -> None:
    init_file = OUTPUT_DIR / "__init__.py"
    init_file.write_text(
        '"""Generated Dart parser (Dart SDK spec grammar v0.60)."""\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
