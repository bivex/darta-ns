import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import darta.infrastructure.antlr.control_flow_extractor as control_flow_module
import darta.presentation.cli.main as cli_main_module
from darta.application.control_flow import (
    BuildNassiDiagramCommand,
    BuildNassiDirectoryCommand,
    NassiDiagramService,
)
from darta.domain.control_flow import (
    ActionFlowStep,
    ControlFlowDiagram,
    ForInFlowStep,
    FunctionControlFlow,
    IfFlowStep,
)
from darta.domain.errors import ControlFlowExtractionError
from darta.domain.model import SourceUnit, SourceUnitId
from darta.infrastructure.antlr.control_flow_extractor import AntlrDartControlFlowExtractor
from darta.infrastructure.filesystem.source_repository import FileSystemSourceRepository
from darta.infrastructure.rendering.nassi_html_renderer import HtmlNassiDiagramRenderer


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


def _build_service() -> NassiDiagramService:
    _ensure_generated_parser()
    return NassiDiagramService(
        source_repository=FileSystemSourceRepository(),
        extractor=AntlrDartControlFlowExtractor(),
        renderer=HtmlNassiDiagramRenderer(),
    )


def test_nassi_service_builds_html_document() -> None:
    service = _build_service()
    document = service.build_file_diagram(
        BuildNassiDiagramCommand(path=str(ROOT / "tests" / "fixtures" / "control_flow.dart"))
    )

    assert document.function_count == 2
    assert "score" in document.function_names
    assert "MathBox.normalize" in document.function_names
    assert "While total &gt; 100" in document.html
    assert "switch category" in document.html
    assert "Darta" in document.html


def test_nassi_service_builds_directory_bundle() -> None:
    service = _build_service()
    bundle = service.build_directory_diagrams(
        BuildNassiDirectoryCommand(root_path=str(ROOT / "tests" / "fixtures"))
    )

    assert bundle.document_count == 3
    assert bundle.root_path == str((ROOT / "tests" / "fixtures").resolve())
    assert any(document.source_location.endswith("control_flow.dart") for document in bundle.documents)
    assert any(document.function_count == 2 for document in bundle.documents)


def test_nassi_service_handles_class_container(tmp_path: Path) -> None:
    service = _build_service()
    source_path = tmp_path / "class_fixture.dart"
    source_path.write_text(
        """
class Direction {
  int score() {
    return 1;
  }
}
""".strip(),
        encoding="utf-8",
    )

    document = service.build_file_diagram(BuildNassiDiagramCommand(path=str(source_path)))

    assert document.function_count == 1
    assert document.function_names == ("Direction.score",)
    assert "Direction" in document.html


def test_nassi_diagram_renders_constructor_initializers_and_await_assignments() -> None:
    service = _build_service()
    document = service.build_file_diagram(
        BuildNassiDiagramCommand(path=str(ROOT / "examples" / "feature_tour.dart"))
    )

    assert "Vector2.fromAngle" in document.function_names
    assert "Action x = length * _cos(radians)" in document.html
    assert "Action y = length * _sin(radians)" in document.html
    assert "Await source" in document.html
    assert "final raw = &lt;await result&gt;;" in document.html
    assert "Return &lt;await result&gt;" in document.html
    assert "_recordTag(_tag(&lt;await result&gt;));" in document.html
    assert "combined += &lt;await result&gt;;" in document.html
    assert "Return _tag(&lt;await result&gt;)" in document.html
    assert "Await for final event in Stream.fromIterable([1, 2, 3])" in document.html
    assert "return switch (n)" in document.html
    assert "return switch (code)" in document.html


def test_nassi_diagram_renders_switch_expression_steps_in_multiple_contexts(tmp_path: Path) -> None:
    service = _build_service()
    source_path = tmp_path / "switch_expression.dart"
    source_path.write_text(
        """
String classify(int value) {
  final label = switch (value) {
    > 0 => 'positive',
    _ => 'other',
  };

  currentStatus = switch (value) {
    0 => 'zero',
    _ => label,
  };

  return switch (value) {
    1 => 'one',
    _ => currentStatus,
  };
}

void emitMode(int mode) {
  switch (mode) {
    0 => print('zero'),
    _ => print('other'),
  };
}
""".strip(),
        encoding="utf-8",
    )

    document = service.build_file_diagram(BuildNassiDiagramCommand(path=str(source_path)))

    assert "final label = switch (value)" in document.html
    assert "currentStatus = switch (value)" in document.html
    assert "return switch (value)" in document.html
    assert "switch (mode)" in document.html
    assert document.html.count('<span class="step-tag">switch</span>') >= 4


def test_nassi_diagram_lifts_embedded_awaits_into_explicit_steps(tmp_path: Path) -> None:
    service = _build_service()
    source_path = tmp_path / "embedded_awaits.dart"
    source_path.write_text(
        """
Future<String> relay(Future<String> source) async {
  return await source;
}

Future<String> decorate(Future<String> source) async {
  var current = '';
  final wrapped = tag(await source);
  logMessage(tag(await source));
  current += await source;
  return tag(await source);
}

String tag(String value) => '[$value]';

void logMessage(String value) {}
""".strip(),
        encoding="utf-8",
    )

    document = service.build_file_diagram(BuildNassiDiagramCommand(path=str(source_path)))

    assert document.html.count("Await source") >= 4
    assert "Return &lt;await result&gt;" in document.html
    assert "final wrapped = tag(&lt;await result&gt;);" in document.html
    assert "logMessage(tag(&lt;await result&gt;));" in document.html
    assert "current += &lt;await result&gt;;" in document.html
    assert "Return tag(&lt;await result&gt;)" in document.html


def test_nassi_cli_writes_html_file(tmp_path: Path) -> None:
    _ensure_generated_parser()
    output_path = tmp_path / "control_flow.html"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "darta.presentation.cli.main",
            "nassi-file",
            str(ROOT / "tests" / "fixtures" / "control_flow.dart"),
            "--out",
            str(output_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["function_count"] == 2
    assert payload["output_path"] == str(output_path.resolve())
    assert output_path.exists()
    assert "Nassi-Shneiderman Control Flow" in output_path.read_text(encoding="utf-8")


def test_nassi_dir_cli_writes_html_bundle(tmp_path: Path) -> None:
    _ensure_generated_parser()
    output_dir = tmp_path / "nassi-bundle"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "darta.presentation.cli.main",
            "nassi-dir",
            str(ROOT / "tests" / "fixtures"),
            "--out",
            str(output_dir),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["document_count"] == 3
    assert payload["output_dir"] == str(output_dir.resolve())
    assert payload["index_path"] == str((output_dir / "index.html").resolve())
    assert len(payload["documents"]) == 3
    assert (output_dir / "index.html").exists()
    assert (output_dir / "control_flow.nassi.html").exists()
    assert (output_dir / "invalid.nassi.html").exists()
    assert "Darta NSD Index" in (output_dir / "index.html").read_text(encoding="utf-8")


def test_control_flow_extractor_raises_explicit_error_on_runtime_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ensure_generated_parser()
    extractor = AntlrDartControlFlowExtractor()
    source_unit = SourceUnit(
        identifier=SourceUnitId("/tmp/failure.dart"),
        location="/tmp/failure.dart",
        content="void main() {}",
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("visitor exploded")

    monkeypatch.setattr(control_flow_module, "parse_source_text", boom)

    with pytest.raises(ControlFlowExtractionError, match="unable to extract control flow"):
        extractor.extract(source_unit)


def test_nassi_cli_returns_json_error_for_control_flow_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "broken.dart"
    source_path.write_text("void main() {}", encoding="utf-8")

    class FailingNassiService:
        def build_file_diagram(self, _command):
            raise ControlFlowExtractionError("unable to extract control flow from broken.dart: boom")

    monkeypatch.setattr(cli_main_module, "_build_nassi_service", lambda: FailingNassiService())

    exit_code = cli_main_module.main(
        [
            "nassi-file",
            str(source_path),
            "--out",
            str(tmp_path / "broken.nassi.html"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    payload = json.loads(captured.err)
    assert "unable to extract control flow" in payload["error"]


def test_nassi_file_cli_returns_json_error_for_invalid_output_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocking_path = tmp_path / "occupied"
    blocking_path.write_text("busy", encoding="utf-8")

    exit_code = cli_main_module.main(
        [
            "nassi-file",
            str(ROOT / "tests" / "fixtures" / "control_flow.dart"),
            "--out",
            str(blocking_path / "diagram.html"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    payload = json.loads(captured.err)
    assert "output directory path is not a directory" in payload["error"]


def test_nassi_dir_cli_returns_json_error_for_invalid_output_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocking_path = tmp_path / "occupied"
    blocking_path.write_text("busy", encoding="utf-8")

    exit_code = cli_main_module.main(
        [
            "nassi-dir",
            str(ROOT / "tests" / "fixtures"),
            "--out",
            str(blocking_path / "bundle"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    payload = json.loads(captured.err)
    assert "output directory path is not a directory" in payload["error"]


# ---------------------------------------------------------------------------
# If depth rendering tests
# ---------------------------------------------------------------------------


class TestIfDepthRendering:
    """If-cap rendering with depth-coded badges and colors."""

    def test_depth_badge_zero_is_empty(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        assert renderer._depth_badge(0) == ""

    def test_depth_badges_1_to_10_use_circled_digits(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        assert renderer._depth_badge(1) == " ①"
        assert renderer._depth_badge(5) == " ⑤"
        assert renderer._depth_badge(10) == " ⑩"

    def test_depth_badges_11_to_20_use_second_range(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        assert renderer._depth_badge(11) == " ⑪"
        assert renderer._depth_badge(15) == " ⑮"
        assert renderer._depth_badge(20) == " ⑳"

    def test_depth_badges_21_to_35_use_third_range(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        assert renderer._depth_badge(21) == " ㉑"
        assert renderer._depth_badge(30) == " ㉚"
        assert renderer._depth_badge(35) == " ㉟"

    def test_depth_badges_36_to_50_use_fourth_range(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        assert renderer._depth_badge(36) == " ㊱"
        assert renderer._depth_badge(40) == " ㊵"
        assert renderer._depth_badge(50) == " ㊿"

    def test_depth_css_generates_51_levels(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        css = renderer._depth_css()
        assert ".ns-if-depth-0-triangle" in css
        assert ".ns-if-depth-50-triangle" in css

    def test_depth_css_cycles_colors(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        css = renderer._depth_css()
        assert "var(--blue-dim)" in css
        assert "var(--green-dim)" in css
        assert "var(--purple-dim)" in css
        assert "var(--teal-dim)" in css
        assert "var(--amber-dim)" in css

    def test_depth_css_includes_body_gradients(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        css = renderer._depth_css()
        assert ".ns-if-depth-0-triangle" in css
        assert ".ns-if-depth-0-diagonal" in css

    def test_render_if_cap_at_depth_zero(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=0)
        assert 'class="ns-if-cap ns-if-depth-0"' in html
        assert '<svg class="ns-if-svg"' in html
        assert "x &gt; 0" in html
        assert 'width="400"' in html
        assert 'height="72"' in html

    def test_render_if_cap_at_depth_five(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=5)
        assert 'class="ns-if-cap ns-if-depth-5"' in html
        assert "⑤" in html

    def test_render_if_cap_at_depth_twenty_clips_badge(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=20)
        assert 'class="ns-if-cap ns-if-depth-20"' in html
        assert "⑳" in html

    def test_render_if_cap_at_depth_thirty_five(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=35)
        assert 'class="ns-if-cap ns-if-depth-35"' in html
        assert "㉟" in html

    def test_render_if_cap_at_depth_thirty_six_jumps_unicode(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=36)
        assert 'class="ns-if-cap ns-if-depth-36"' in html
        assert "㊱" in html

    def test_render_if_cap_at_depth_fifty(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=50)
        assert 'class="ns-if-cap ns-if-depth-50"' in html
        assert "㊿" in html

    def test_render_if_cap_clips_at_max_depth(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap("x > 0", depth=100)
        assert 'class="ns-if-cap ns-if-depth-50"' in html
        assert "㊿" in html

    def test_render_if_cap_expands_svg_for_long_conditions(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_if_cap(
            "request.user.profile.permissions.canAccessScopedResource && "
            "request.executionContext.region.isAllowedForThisOperation",
            depth=2,
        )
        match = re.search(r'viewBox="0 0 (\d+) (\d+)"', html)
        assert match is not None
        width = int(match.group(1))
        height = int(match.group(2))
        assert width > 400
        assert height >= 72

    def test_nested_ifs_in_html_output(self) -> None:
        service = _build_service()
        document = service.build_file_diagram(
            BuildNassiDiagramCommand(path=str(ROOT / "tests" / "fixtures" / "control_flow.dart"))
        )
        html = document.html
        assert "ns-if-depth-" in html

    def test_nested_if_layout_css_can_expand_horizontally_for_deep_branches(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        diagram = ControlFlowDiagram(
            source_location="nested.dart",
            functions=(
                FunctionControlFlow(
                    name="processComplexData",
                    signature="processComplexData(List<Item> data)",
                    container=None,
                    steps=(
                        IfFlowStep(
                            condition="item.isValid",
                            then_steps=(
                                IfFlowStep(
                                    condition="item.hasPriority",
                                    then_steps=(ActionFlowStep("handleUrgent(item)"),),
                                    else_steps=(ActionFlowStep("handleNormal(item)"),),
                                ),
                            ),
                            else_steps=(
                                IfFlowStep(
                                    condition="item.canRecover",
                                    then_steps=(ActionFlowStep("recover(item)"),),
                                    else_steps=(ActionFlowStep("discard(item)"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        css = renderer.render(diagram).split("<style>", 1)[1].split("</style>", 1)[0]

        assert re.search(
            r"\.viewer \{[^}]*width: max-content;[^}]*min-width: min\(1200px, calc\(100vw - 48px\)\);",
            css,
            re.DOTALL,
        )
        assert re.search(
            r"\.function-body > \.ns-sequence \{[^}]*width: max-content;[^}]*min-width: 100%;",
            css,
            re.DOTALL,
        )
        assert re.search(
            r"\.ns-sequence \{[^}]*width: max-content;[^}]*min-width: 100%;",
            css,
            re.DOTALL,
        )
        assert re.search(
            r"\.ns-branches \{[^}]*grid-template-columns: repeat\(2, max-content\);[^}]*width: max-content;[^}]*min-width: 100%;",
            css,
            re.DOTALL,
        )
        assert "580px" not in css

    def test_if_branches_use_green_and_red_highlight_classes(self) -> None:
        renderer = HtmlNassiDiagramRenderer()
        html = renderer._render_step(
            IfFlowStep(
                condition="flag",
                then_steps=(ActionFlowStep("return success"),),
                else_steps=(ActionFlowStep("return failure"),),
            ),
            depth=0,
        )

        assert 'class="ns-branch ns-branch-yes"' in html
        assert 'class="ns-branch ns-branch-no"' in html
        assert "rgba(158, 206, 106" in renderer.render(
            ControlFlowDiagram(
                source_location="branch-colors.dart",
                functions=(
                    FunctionControlFlow(
                        name="f",
                        signature="f()",
                        container=None,
                        steps=(
                            IfFlowStep(
                                condition="flag",
                                then_steps=(ActionFlowStep("return success"),),
                                else_steps=(ActionFlowStep("return failure"),),
                            ),
                        ),
                    ),
                ),
            )
        )
        assert "rgba(247, 118, 142" in renderer.render(
            ControlFlowDiagram(
                source_location="branch-colors.dart",
                functions=(
                    FunctionControlFlow(
                        name="f",
                        signature="f()",
                        container=None,
                        steps=(
                            IfFlowStep(
                                condition="flag",
                                then_steps=(ActionFlowStep("return success"),),
                                else_steps=(ActionFlowStep("return failure"),),
                            ),
                        ),
                    ),
                ),
            )
        )
