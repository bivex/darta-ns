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
            # Dart3: typeAlias has typeWithParameters or functionTypeAlias
            twp = ctx.typeWithParameters() if hasattr(ctx, "typeWithParameters") else None
            if twp is not None:
                name = twp.typeIdentifier().getText()
            else:
                fta = ctx.functionTypeAlias() if hasattr(ctx, "functionTypeAlias") else None
                if fta is not None and fta.functionPrefix() is not None:
                    fp = fta.functionPrefix()
                    name = fp.identifier().getText() if fp.identifier() else "typedef"
                else:
                    name = "typedef"
            self._append(
                StructuralElementKind.TYPE_ALIAS,
                name,
                ctx,
                signature=f"typedef {name}",
            )
            return None

        def visitEnumType(self, ctx):
            # Dart3: enumType uses classNameMaybePrimary
            name = _name_from_class_name_maybe_primary(ctx.classNameMaybePrimary())
            self._append(StructuralElementKind.ENUM, name, ctx, signature=f"enum {name}")
            return None

        def visitClassDeclaration(self, ctx):
            cnmp = ctx.classNameMaybePrimary() if hasattr(ctx, "classNameMaybePrimary") else None
            name = _name_from_class_name_maybe_primary(cnmp) if cnmp else "class"
            self._append(StructuralElementKind.CLASS, name, ctx, signature=f"class {name}")
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitMixinDeclaration(self, ctx):
            twp = ctx.typeWithParameters() if hasattr(ctx, "typeWithParameters") else None
            name = twp.typeIdentifier().getText() if twp is not None else "mixin"
            self._append(StructuralElementKind.MIXIN, name, ctx, signature=f"mixin {name}")
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitExtensionDeclaration(self, ctx):
            tint = ctx.typeIdentifierNotType() if hasattr(ctx, "typeIdentifierNotType") else None
            name = tint.getText() if tint is not None else "extension"
            self._append(
                StructuralElementKind.EXTENSION,
                name,
                ctx,
                signature=f"extension {name}",
            )
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitExtensionTypeDeclaration(self, ctx):
            # extensionTypeDeclaration: EXTENSION TYPE primaryConstructor ...
            # or AUGMENT EXTENSION TYPE typeWithParameters ...
            pc = ctx.primaryConstructor() if hasattr(ctx, "primaryConstructor") else None
            if pc is not None:
                name = pc.typeWithParameters().typeIdentifier().getText()
            else:
                twp = ctx.typeWithParameters() if hasattr(ctx, "typeWithParameters") else None
                name = twp.typeIdentifier().getText() if twp is not None else "extension type"
            self._append(
                StructuralElementKind.EXTENSION,
                name,
                ctx,
                signature=f"extension type {name}",
            )
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitTopLevelDeclaration(self, ctx):
            # functionSignature functionBody (not AUGMENT-only or EXTERNAL-only)
            if (
                ctx.functionSignature() is not None
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
                ident = getter.identifier()
                base_name = ident.getText() if ident else "get"
                name = f"get {base_name}"
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=f"get {base_name}",
                )
                return None

            # setterSignature functionBody
            if ctx.setterSignature() is not None and ctx.functionBody() is not None:
                setter = ctx.setterSignature()
                ident = setter.identifier()
                base_name = ident.getText() if ident else "set"
                name = f"set {base_name}"
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=f"set {base_name}",
                )
                return None

            # Top-level variables/constants — skip, visit children for class/etc.
            return self.visitChildren(ctx)

        # ── Class members ───────────────────────────────────────────────────

        def visitMemberDeclaration(self, ctx):
            if ctx.methodSignature() is None or ctx.functionBody() is None:
                return self.visitChildren(ctx)
            method_sig = ctx.methodSignature()

            # functionSignature
            func_sig = method_sig.functionSignature() if hasattr(method_sig, "functionSignature") else None
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

            # getterSignature
            getter_sig = method_sig.getterSignature() if hasattr(method_sig, "getterSignature") else None
            if getter_sig is not None:
                ident = getter_sig.identifier()
                base_name = ident.getText() if ident else "get"
                name = f"get {base_name}"
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=f"get {base_name}",
                )
                return None

            # setterSignature
            setter_sig = method_sig.setterSignature() if hasattr(method_sig, "setterSignature") else None
            if setter_sig is not None:
                ident = setter_sig.identifier()
                base_name = ident.getText() if ident else "set"
                name = f"set {base_name}"
                self._append(
                    StructuralElementKind.FUNCTION,
                    name,
                    ctx,
                    signature=f"set {base_name}",
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


def _name_from_class_name_maybe_primary(cnmp) -> str:
    """Extract the type name from a classNameMaybePrimary context."""
    if cnmp is None:
        return "class"
    # classNameMaybePrimary: primaryConstructor | typeWithParameters
    twp = cnmp.typeWithParameters() if hasattr(cnmp, "typeWithParameters") else None
    if twp is not None:
        return twp.typeIdentifier().getText()
    pc = cnmp.primaryConstructor() if hasattr(cnmp, "primaryConstructor") else None
    if pc is not None:
        return pc.typeWithParameters().typeIdentifier().getText()
    return "class"
