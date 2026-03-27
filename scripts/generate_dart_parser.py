"""Generate Python parser artifacts from the vendored Dart grammar."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "build" / "tools"
GRAMMAR_DIR = ROOT / "resources" / "grammars" / "dart2"
OUTPUT_DIR = ROOT / "src" / "darta" / "infrastructure" / "antlr" / "generated" / "dart2"
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
    _write_support_modules()
    _generate_parser()
    _ensure_package_files()


def _ensure_grammar_exists() -> None:
    required = (
        GRAMMAR_DIR / "Dart2Lexer.g4",
        GRAMMAR_DIR / "Dart2Parser.g4",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing grammar files: {', '.join(missing)}")


def _ensure_antlr_jar_exists() -> None:
    if ANTLR_JAR.exists():
        return
    print(f"Downloading ANTLR {ANTLR_VERSION}...")
    urlretrieve(ANTLR_JAR_URL, ANTLR_JAR)


def _write_support_modules() -> None:
    (OUTPUT_DIR / "Dart2LexerBase.py").write_text(
        dedent(
            '''
            from __future__ import annotations

            import sys

            from antlr4 import Lexer

            if sys.version_info[1] > 5:
                from typing import TextIO
            else:
                from typing.io import TextIO


            class Dart2LexerBase(Lexer):
                """Base class for the generated Dart2 lexer.

                Provides the semantic predicate used to distinguish bare ``$``
                interpolation from the ``${`` block form inside string literals.
                """

                def __init__(self, input=None, output: TextIO = sys.stdout):
                    super().__init__(input, output)

                def CheckNotOpenBrace(self) -> bool:
                    """Return True when the lookahead character is not ``{``."""
                    return self._input.LA(1) != ord("{")
            '''
        ).lstrip(),
        encoding="utf-8",
    )


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
        str(GRAMMAR_DIR / "Dart2Lexer.g4"),
        str(GRAMMAR_DIR / "Dart2Parser.g4"),
    ]
    subprocess.run(command, check=True, cwd=ROOT)


def _ensure_package_files() -> None:
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Generated Dart ANTLR parser."""\n', encoding="utf-8")


if __name__ == "__main__":
    main()
