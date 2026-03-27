"""ANTLR-backed Dart parser adapter."""

from __future__ import annotations

from time import perf_counter

from darta.domain.model import (
    GrammarVersion,
    ParseOutcome,
    ParseStatistics,
    SourceUnit,
    StructuralElement,
    StructuralElementKind,
)
from darta.domain.ports import DartSyntaxParser
from darta.infrastructure.antlr.runtime import (
    ANTLR_GRAMMAR_VERSION,
    load_generated_types,
    parse_source_text,
)


class AntlrDartSyntaxParser(DartSyntaxParser):
    def __init__(self) -> None:
        self._generated = load_generated_types()

    @property
    def grammar_version(self) -> GrammarVersion:
        return ANTLR_GRAMMAR_VERSION

    def parse(self, source_unit: SourceUnit) -> ParseOutcome:
        started_at = perf_counter()
        try:
            parse_result = parse_source_text(source_unit.content, self._generated)
            structure_visitor = _build_structure_visitor(self._generated.visitor_type)()
            structure_visitor.visit(parse_result.tree)

            elements = tuple(structure_visitor.elements)
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)

            return ParseOutcome.success(
                source_unit=source_unit,
                grammar_version=self.grammar_version,
                diagnostics=parse_result.diagnostics,
                structural_elements=elements,
                statistics=ParseStatistics(
                    token_count=len(parse_result.token_stream.tokens),
                    structural_element_count=len(elements),
                    diagnostic_count=len(parse_result.diagnostics),
                    elapsed_ms=elapsed_ms,
                ),
            )
        except Exception as error:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
            return ParseOutcome.technical_failure(
                source_unit=source_unit,
                grammar_version=self.grammar_version,
                message=str(error),
                elapsed_ms=elapsed_ms,
            )


def _build_structure_visitor(visitor_base: type) -> type:
    class DartStructureVisitor(visitor_base):
        def __init__(self) -> None:
            super().__init__()
            self.elements: list[StructuralElement] = []
            self._containers: list[str] = []

        # ── Top-level declarations ──────────────────────────────────────────

        def visitImportSpecification(self, ctx):
            uri_text = ctx.configurableUri().getText() if ctx.configurableUri() else ""
            self._append(
                StructuralElementKind.IMPORT,
                uri_text,
                ctx,
                signature=f"import {uri_text}",
            )
            return None

        def visitTypeAlias(self, ctx):
            name = ctx.typeIdentifier().getText() if ctx.typeIdentifier() else "typedef"
            self._append(
                StructuralElementKind.TYPE_ALIAS,
                name,
                ctx,
                signature=f"typedef {name}",
            )
            return None

        def visitEnumType(self, ctx):
            name = ctx.identifier().getText() if ctx.identifier() else "enum"
            self._append(StructuralElementKind.ENUM, name, ctx, signature=f"enum {name}")
            return None

        def visitClassDeclaration(self, ctx):
            name = ctx.typeIdentifier().getText() if ctx.typeIdentifier() else "class"
            self._append(StructuralElementKind.CLASS, name, ctx, signature=f"class {name}")
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitMixinDeclaration(self, ctx):
            name = ctx.typeIdentifier().getText() if ctx.typeIdentifier() else "mixin"
            self._append(StructuralElementKind.MIXIN, name, ctx, signature=f"mixin {name}")
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitExtensionDeclaration(self, ctx):
            name_ctx = ctx.identifier()
            name = name_ctx.getText() if name_ctx else "extension"
            self._append(
                StructuralElementKind.EXTENSION,
                name,
                ctx,
                signature=f"extension {name}",
            )
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitTopLevelDeclaration(self, ctx):
            # functionSignature functionBody (not EXTERNAL_)
            if (
                ctx.EXTERNAL_() is None
                and ctx.functionSignature() is not None
                and ctx.functionBody() is not None
            ):
                func_sig = ctx.functionSignature()
                name = func_sig.identifier().getText() if func_sig.identifier() else "function"
                sig = func_sig.getText()
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=sig,
                )
                return None

            # getterSignature functionBody
            if ctx.getterSignature() is not None and ctx.functionBody() is not None:
                getter = ctx.getterSignature()
                name = getter.identifier().getText() if getter.identifier() else "get"
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=f"get {name}",
                )
                return None

            # Top-level variables/constants — skip, visit children for class/etc.
            return self.visitChildren(ctx)

        # ── Class members ───────────────────────────────────────────────────

        def visitClassMemberDeclaration(self, ctx):
            if ctx.methodSignature() is not None and ctx.functionBody() is not None:
                method_sig = ctx.methodSignature()
                func_sig = method_sig.functionSignature() if method_sig.functionSignature() else None
                if func_sig is not None:
                    name = func_sig.identifier().getText() if func_sig.identifier() else "method"
                    sig = func_sig.getText()
                    self._append(
                        StructuralElementKind.FUNCTION,
                        name,
                        ctx,
                        signature=sig,
                    )
                    return None
            return self.visitChildren(ctx)

        # ── Helpers ─────────────────────────────────────────────────────────

        def _append(self, kind, name: str, ctx, signature: str | None = None) -> None:
            container = ".".join(self._containers) if self._containers else None
            self.elements.append(
                StructuralElement(
                    kind=kind,
                    name=name,
                    line=ctx.start.line,
                    column=ctx.start.column,
                    container=container,
                    signature=signature,
                )
            )

        def _with_container(self, name: str, callback):
            self._containers.append(name)
            try:
                return callback()
            finally:
                self._containers.pop()

    return DartStructureVisitor
