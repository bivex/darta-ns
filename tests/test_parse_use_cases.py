import json
import os
import subprocess
import sys
from pathlib import Path

from darta.application.dto import ParseDirectoryCommand, ParseFileCommand
from darta.application.use_cases import ParsingJobService
from darta.infrastructure.antlr.parser_adapter import AntlrDartSyntaxParser
from darta.infrastructure.filesystem.source_repository import FileSystemSourceRepository
from darta.infrastructure.system import (
    InMemoryParsingJobRepository,
    StructuredLoggingEventPublisher,
    SystemClock,
)


ROOT = Path(__file__).resolve().parent.parent


def _ensure_generated_parser() -> None:
    generated_parser = (
        ROOT / "src" / "darta" / "infrastructure" / "antlr" / "generated" / "dart3" / "DartParser.py"
    )
    if generated_parser.exists():
        return
    subprocess.run(
        [sys.executable, "scripts/generate_dart_parser.py"],
        cwd=ROOT,
        check=True,
    )


def _build_service() -> ParsingJobService:
    _ensure_generated_parser()
    return ParsingJobService(
        source_repository=FileSystemSourceRepository(),
        parser=AntlrDartSyntaxParser(),
        event_publisher=StructuredLoggingEventPublisher(),
        clock=SystemClock(),
        job_repository=InMemoryParsingJobRepository(),
    )


def test_parse_file_extracts_structure() -> None:
    service = _build_service()
    report = service.parse_file(ParseFileCommand(path=str(ROOT / "tests" / "fixtures" / "valid.dart")))

    assert report.summary.source_count == 1
    assert report.summary.technical_failure_count == 0
    assert report.sources[0].status in {"succeeded", "succeeded_with_diagnostics"}
    assert {element.kind for element in report.sources[0].structural_elements} >= {
        "import",
        "class",
        "function",
    }


def test_parse_directory_returns_report_for_all_files() -> None:
    service = _build_service()
    report = service.parse_directory(ParseDirectoryCommand(root_path=str(ROOT / "tests" / "fixtures")))

    assert report.summary.source_count == 3
    assert len(report.sources) == 3


def test_parse_file_handles_enum_declaration(tmp_path: Path) -> None:
    service = _build_service()
    source_path = tmp_path / "enum_parse.dart"
    source_path.write_text(
        """
enum Mode {
  active,
  inactive;

  String get title => name;
}
""".strip(),
        encoding="utf-8",
    )

    report = service.parse_file(ParseFileCommand(path=str(source_path)))

    assert report.summary.source_count == 1
    assert report.summary.technical_failure_count == 0
    assert {element.kind for element in report.sources[0].structural_elements} >= {"enum"}


def test_cli_outputs_json() -> None:
    _ensure_generated_parser()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "darta.presentation.cli.main",
            "parse-file",
            str(ROOT / "tests" / "fixtures" / "valid.dart"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["source_count"] == 1
