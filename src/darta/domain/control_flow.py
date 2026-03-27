"""Domain model for structured control flow diagrams."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControlFlowStep:
    """Base type for a structured control flow step."""


@dataclass(frozen=True, slots=True)
class ActionFlowStep(ControlFlowStep):
    label: str


@dataclass(frozen=True, slots=True)
class AwaitFlowStep(ControlFlowStep):
    expression: str


@dataclass(frozen=True, slots=True)
class YieldFlowStep(ControlFlowStep):
    expression: str
    is_each: bool  # True for yield*, False for yield


@dataclass(frozen=True, slots=True)
class RethrowFlowStep(ControlFlowStep):
    pass


@dataclass(frozen=True, slots=True)
class AssertFlowStep(ControlFlowStep):
    condition: str
    message: str | None


@dataclass(frozen=True, slots=True)
class BreakFlowStep(ControlFlowStep):
    label: str | None


@dataclass(frozen=True, slots=True)
class ContinueFlowStep(ControlFlowStep):
    label: str | None


@dataclass(frozen=True, slots=True)
class ThrowFlowStep(ControlFlowStep):
    expression: str


@dataclass(frozen=True, slots=True)
class ReturnFlowStep(ControlFlowStep):
    expression: str | None


@dataclass(frozen=True, slots=True)
class PatternDeclarationFlowStep(ControlFlowStep):
    """Pattern variable declaration like `var (a, b) = pair` or `final Point(:x) = p`."""
    keyword: str  # "var" or "final"
    pattern: str
    expression: str


@dataclass(frozen=True, slots=True)
class IfFlowStep(ControlFlowStep):
    condition: str
    then_steps: tuple[ControlFlowStep, ...]
    else_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class WhileFlowStep(ControlFlowStep):
    condition: str
    body_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class DoWhileFlowStep(ControlFlowStep):
    condition: str
    body_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class ForInFlowStep(ControlFlowStep):
    header: str
    is_await: bool  # True for "await for"
    body_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class SwitchCaseFlow:
    label: str
    steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class SwitchFlowStep(ControlFlowStep):
    expression: str
    cases: tuple[SwitchCaseFlow, ...]


@dataclass(frozen=True, slots=True)
class SwitchExpressionFlowStep(ControlFlowStep):
    """Dart 3 switch expression: `final x = switch(v) { p => e, ... }`"""
    expression: str  # The full switch expression text


@dataclass(frozen=True, slots=True)
class CatchClauseFlow:
    pattern: str
    steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class TryCatchFlowStep(ControlFlowStep):
    body_steps: tuple[ControlFlowStep, ...]
    catches: tuple[CatchClauseFlow, ...]
    finally_steps: tuple[ControlFlowStep, ...]


@dataclass(frozen=True, slots=True)
class FunctionControlFlow:
    name: str
    signature: str
    container: str | None
    steps: tuple[ControlFlowStep, ...]

    @property
    def qualified_name(self) -> str:
        if self.container:
            return f"{self.container}.{self.name}"
        return self.name


@dataclass(frozen=True, slots=True)
class ControlFlowDiagram:
    source_location: str
    functions: tuple[FunctionControlFlow, ...]

