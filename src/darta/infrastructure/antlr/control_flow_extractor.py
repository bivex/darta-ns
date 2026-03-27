"""Extract structured control flow from Dart source through ANTLR."""

from __future__ import annotations

import re
from dataclasses import dataclass

from darta.domain.control_flow import (
    ActionFlowStep,
    AssertFlowStep,
    AwaitFlowStep,
    BreakFlowStep,
    CatchClauseFlow,
    ContinueFlowStep,
    ControlFlowDiagram,
    ControlFlowStep,
    DoWhileFlowStep,
    ForInFlowStep,
    FunctionControlFlow,
    IfFlowStep,
    PatternDeclarationFlowStep,
    RethrowFlowStep,
    ReturnFlowStep,
    SwitchCaseFlow,
    SwitchFlowStep,
    ThrowFlowStep,
    TryCatchFlowStep,
    WhileFlowStep,
    YieldFlowStep,
)
from darta.domain.model import SourceUnit
from darta.domain.ports import DartControlFlowExtractor
from darta.infrastructure.antlr.runtime import (
    load_generated_types,
    parse_source_text,
)


@dataclass(frozen=True, slots=True)
class _ExtractorContext:
    token_stream: object

    def text(self, ctx) -> str:
        if ctx is None:
            return ""
        input_stream = self.token_stream.tokenSource.inputStream
        return input_stream.getText(ctx.start.start, ctx.stop.stop)

    def compact(self, ctx, *, limit: int = 96) -> str:
        text = re.sub(r"\s+", " ", self.text(ctx)).strip()
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1]}..."


class AntlrDartControlFlowExtractor(DartControlFlowExtractor):
    def __init__(self) -> None:
        self._generated = load_generated_types()

    def extract(self, source_unit: SourceUnit) -> ControlFlowDiagram:
        try:
            parse_result = parse_source_text(source_unit.content, self._generated)
            ctx = _ExtractorContext(token_stream=parse_result.token_stream)
            visitor = _build_control_flow_visitor(self._generated.visitor_type, ctx)()
            visitor.visit(parse_result.tree)
            return ControlFlowDiagram(
                source_location=source_unit.location,
                functions=tuple(visitor.functions),
            )
        except Exception:
            return ControlFlowDiagram(source_location=source_unit.location, functions=())


def _build_control_flow_visitor(visitor_base: type, context: _ExtractorContext) -> type:
    class DartControlFlowVisitor(visitor_base):
        def __init__(self) -> None:
            super().__init__()
            self.functions: list[FunctionControlFlow] = []
            self._containers: list[str] = []

        # ── Container tracking ──────────────────────────────────────────────

        def visitClassDeclaration(self, ctx):
            cnmp = ctx.classNameMaybePrimary() if hasattr(ctx, "classNameMaybePrimary") else None
            name = _name_from_class_name_maybe_primary(cnmp) if cnmp else "class"
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitMixinDeclaration(self, ctx):
            twp = ctx.typeWithParameters() if hasattr(ctx, "typeWithParameters") else None
            name = twp.typeIdentifier().getText() if twp is not None else "mixin"
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitExtensionDeclaration(self, ctx):
            tint = ctx.typeIdentifierNotType() if hasattr(ctx, "typeIdentifierNotType") else None
            name = tint.getText() if tint is not None else "extension"
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitExtensionTypeDeclaration(self, ctx):
            pc = ctx.primaryConstructor() if hasattr(ctx, "primaryConstructor") else None
            if pc is not None:
                name = pc.typeWithParameters().typeIdentifier().getText()
            else:
                twp = ctx.typeWithParameters() if hasattr(ctx, "typeWithParameters") else None
                name = twp.typeIdentifier().getText() if twp is not None else "extension type"
            return self._with_container(name, lambda: self.visitChildren(ctx))

        def visitEnumType(self, ctx):
            cnmp = ctx.classNameMaybePrimary() if hasattr(ctx, "classNameMaybePrimary") else None
            name = _name_from_class_name_maybe_primary(cnmp) if cnmp else "enum"
            return self._with_container(name, lambda: self.visitChildren(ctx))

        # ── Function / method discovery ─────────────────────────────────────

        def visitTopLevelDeclaration(self, ctx):
            # functionSignature functionBody
            if (
                ctx.functionSignature() is not None
                and ctx.functionBody() is not None
            ):
                func_sig = ctx.functionSignature()
                name = func_sig.identifier().getText() if func_sig.identifier() else "function"
                sig = context.compact(func_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # getterSignature functionBody
            if ctx.getterSignature() is not None and ctx.functionBody() is not None:
                getter_sig = ctx.getterSignature()
                ident = getter_sig.identifier()
                base_name = ident.getText() if ident else "get"
                name = f"get {base_name}"
                sig = context.compact(getter_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # setterSignature functionBody
            if ctx.setterSignature() is not None and ctx.functionBody() is not None:
                setter_sig = ctx.setterSignature()
                ident = setter_sig.identifier()
                base_name = ident.getText() if ident else "set"
                name = f"set {base_name}"
                sig = context.compact(setter_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            return self.visitChildren(ctx)

        def visitMemberDeclaration(self, ctx):
            if ctx.methodSignature() is None or ctx.functionBody() is None:
                return None
            method_sig = ctx.methodSignature()

            # functionSignature
            func_sig = method_sig.functionSignature() if hasattr(method_sig, "functionSignature") else None
            if func_sig is not None:
                name = func_sig.identifier().getText() if func_sig.identifier() else "method"
                sig = context.compact(func_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # getterSignature
            getter_sig = method_sig.getterSignature() if hasattr(method_sig, "getterSignature") else None
            if getter_sig is not None:
                ident = getter_sig.identifier()
                base_name = ident.getText() if ident else "get"
                name = f"get {base_name}"
                sig = context.compact(getter_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # setterSignature
            setter_sig = method_sig.setterSignature() if hasattr(method_sig, "setterSignature") else None
            if setter_sig is not None:
                ident = setter_sig.identifier()
                base_name = ident.getText() if ident else "set"
                name = f"set {base_name}"
                sig = context.compact(setter_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # constructorSignature (regular and named constructors)
            ctor_sig = method_sig.constructorSignature() if hasattr(method_sig, "constructorSignature") else None
            if ctor_sig is not None:
                cn = ctor_sig.constructorName() if hasattr(ctor_sig, "constructorName") else None
                if cn is not None and cn.typeIdentifier() is not None:
                    id_or_new = cn.identifierOrNew()
                    base = cn.typeIdentifier().getText()
                    name = f"{base}.{id_or_new.getText()}" if id_or_new else base
                else:
                    ch = ctor_sig.constructorHead() if hasattr(ctor_sig, "constructorHead") else None
                    ident = ch.identifier() if ch and hasattr(ch, "identifier") else None
                    name = ident.getText() if ident else "<constructor>"
                sig = context.compact(ctor_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # factoryConstructorSignature
            factory_sig = method_sig.factoryConstructorSignature() if hasattr(method_sig, "factoryConstructorSignature") else None
            if factory_sig is not None:
                sig = context.compact(factory_sig)
                tpn = factory_sig.constructorTwoPartName() if hasattr(factory_sig, "constructorTwoPartName") else None
                if tpn is not None and tpn.identifierOrNew() is not None:
                    name = f"factory {tpn.identifierOrNew().getText()}"
                else:
                    fch = factory_sig.factoryConstructorHead() if hasattr(factory_sig, "factoryConstructorHead") else None
                    ident = fch.identifier() if fch and hasattr(fch, "identifier") else None
                    name = f"factory {ident.getText()}" if ident else "factory"
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            # operatorSignature
            op_sig = method_sig.operatorSignature() if hasattr(method_sig, "operatorSignature") else None
            if op_sig is not None:
                op = op_sig.operator() if hasattr(op_sig, "operator") else None
                op_text = context.compact(op) if op is not None else "?"
                name = f"operator {op_text}"
                sig = context.compact(op_sig)
                self.functions.append(
                    FunctionControlFlow(
                        name=name,
                        signature=sig,
                        container=".".join(self._containers) if self._containers else None,
                        steps=self._extract_function_body(ctx.functionBody()),
                    )
                )
                return None

            return None

        # ── Body / block extraction ─────────────────────────────────────────

        def _extract_function_body(self, function_body_ctx) -> tuple[ControlFlowStep, ...]:
            if function_body_ctx is None:
                return ()
            # Arrow function: (async?) => expression ;
            # Check for expression() in arrow-form — functionBody has expression() when it's =>
            expr = function_body_ctx.expression() if hasattr(function_body_ctx, "expression") else None
            if expr is not None and function_body_ctx.block() is None:
                expr_text = context.compact(expr)
                return (ActionFlowStep(f"=> {expr_text}"),)
            # Block body
            if function_body_ctx.block() is not None:
                return self._extract_block(function_body_ctx.block())
            return ()

        def _extract_block(self, block_ctx) -> tuple[ControlFlowStep, ...]:
            if block_ctx is None or block_ctx.statements() is None:
                return ()
            return self._extract_statements(block_ctx.statements())

        def _extract_statements(self, statements_ctx) -> tuple[ControlFlowStep, ...]:
            steps: list[ControlFlowStep] = []
            for stmt_ctx in statements_ctx.statement():
                step = self._extract_statement(stmt_ctx)
                if step is not None:
                    steps.append(step)
            return tuple(steps)

        def _extract_statement(self, statement_ctx) -> ControlFlowStep | None:
            # statement : label* nonLabelledStatement
            nls = statement_ctx.nonLabelledStatement()
            if nls is None:
                return ActionFlowStep(context.compact(statement_ctx))
            return self._extract_non_labelled_statement(nls)

        def _extract_non_labelled_statement(self, ctx) -> ControlFlowStep | None:
            if ctx.ifStatement() is not None:
                return self._extract_if_statement(ctx.ifStatement())
            if ctx.whileStatement() is not None:
                return self._extract_while_statement(ctx.whileStatement())
            if ctx.doStatement() is not None:
                return self._extract_do_statement(ctx.doStatement())
            if ctx.forStatement() is not None:
                return self._extract_for_statement(ctx.forStatement())
            if ctx.switchStatement() is not None:
                return self._extract_switch_statement(ctx.switchStatement())
            if ctx.tryStatement() is not None:
                return self._extract_try_statement(ctx.tryStatement())
            if ctx.block() is not None:
                steps = self._extract_block(ctx.block())
                if steps:
                    return ActionFlowStep("{ ... }")
                return None
            if ctx.rethrowStatement() is not None:
                return RethrowFlowStep()
            if ctx.returnStatement() is not None:
                rs = ctx.returnStatement()
                expr = rs.expression()
                return ReturnFlowStep(expression=context.compact(expr) if expr else None)
            if ctx.yieldStatement() is not None:
                expr = context.compact(ctx.yieldStatement().expression())
                return YieldFlowStep(expression=expr, is_each=False)
            if hasattr(ctx, "yieldEachStatement") and ctx.yieldEachStatement() is not None:
                yes = ctx.yieldEachStatement()
                expr = context.compact(yes.expression())
                return YieldFlowStep(expression=expr, is_each=True)
            if ctx.assertStatement() is not None:
                ast = ctx.assertStatement().assertion()
                exprs = ast.expression()
                cond = context.compact(exprs[0]) if exprs else ""
                msg = context.compact(exprs[1]) if len(exprs) > 1 else None
                return AssertFlowStep(condition=cond, message=msg)
            if ctx.breakStatement() is not None:
                ident = ctx.breakStatement().identifier()
                return BreakFlowStep(label=ident.getText() if ident else None)
            if ctx.continueStatement() is not None:
                ident = ctx.continueStatement().identifier()
                return ContinueFlowStep(label=ident.getText() if ident else None)
            if ctx.expressionStatement() is not None:
                text = context.compact(ctx.expressionStatement())
                if text.startswith("await "):
                    return AwaitFlowStep(text[len("await "):].rstrip(";").strip())
                if text.startswith("throw "):
                    return ThrowFlowStep(text[len("throw "):].rstrip(";").strip())
                return ActionFlowStep(text)
            if ctx.localVariableDeclaration() is not None:
                lvd = ctx.localVariableDeclaration()
                # Check for patternVariableDeclaration branch
                if hasattr(lvd, "patternVariableDeclaration") and lvd.patternVariableDeclaration() is not None:
                    pv = lvd.patternVariableDeclaration()
                    opp = pv.outerPatternDeclarationPrefix()
                    keyword = "var" if opp.VAR() is not None else "final"
                    pattern = context.compact(opp.outerPattern())
                    expr = context.compact(pv.expression())
                    return PatternDeclarationFlowStep(keyword=keyword, pattern=pattern, expression=expr)
            if ctx.localFunctionDeclaration() is not None:
                lfd = ctx.localFunctionDeclaration()
                func_sig = lfd.functionSignature() if hasattr(lfd, "functionSignature") else None
                if func_sig is not None and func_sig.identifier() is not None:
                    return ActionFlowStep(f"local function {func_sig.identifier().getText()}")
                return ActionFlowStep("local function")
            return ActionFlowStep(context.compact(ctx))

        # ── Statement extractors ────────────────────────────────────────────

        def _extract_statement_as_steps(
            self, statement_ctx
        ) -> tuple[ControlFlowStep, ...]:
            """Return the contents of statement as a step tuple.

            If the statement is a bare block, returns its inner steps.
            Otherwise wraps the single step in a tuple.
            """
            if statement_ctx is None:
                return ()
            nls = statement_ctx.nonLabelledStatement()
            if nls is not None and nls.block() is not None:
                return self._extract_block(nls.block())
            step = self._extract_statement(statement_ctx)
            return (step,) if step is not None else ()

        def _extract_if_statement(self, if_ctx) -> IfFlowStep:
            # Dart3: ifCondition contains expression and optional CASE guardedPattern
            if_cond = if_ctx.ifCondition()
            if if_cond is not None:
                condition = context.compact(if_cond.expression())
                # Check for "case Pattern when guard" suffix
                if if_cond.CASE() is not None and if_cond.guardedPattern() is not None:
                    gp = if_cond.guardedPattern()
                    pattern = context.compact(gp.pattern())
                    condition += f" case {pattern}"
                    if gp.WHEN() is not None and gp.expression() is not None:
                        guard = context.compact(gp.expression())
                        condition += f" when {guard}"
            else:
                condition = "condition"
            statements = if_ctx.statement()
            then_steps = self._extract_statement_as_steps(
                statements[0] if len(statements) > 0 else None
            )
            else_steps: tuple[ControlFlowStep, ...] = ()
            if len(statements) > 1:
                else_stmt = statements[1]
                # Check for else-if chain
                else_nls = else_stmt.nonLabelledStatement()
                if else_nls is not None and else_nls.ifStatement() is not None:
                    else_steps = (self._extract_if_statement(else_nls.ifStatement()),)
                else:
                    else_steps = self._extract_statement_as_steps(else_stmt)
            return IfFlowStep(
                condition=condition or "condition",
                then_steps=then_steps,
                else_steps=else_steps,
            )

        def _extract_while_statement(self, while_ctx) -> WhileFlowStep:
            condition = context.compact(while_ctx.expression())
            body_steps = self._extract_statement_as_steps(while_ctx.statement())
            return WhileFlowStep(condition=condition or "condition", body_steps=body_steps)

        def _extract_do_statement(self, do_ctx) -> DoWhileFlowStep:
            body_steps = self._extract_statement_as_steps(do_ctx.statement())
            condition = context.compact(do_ctx.expression())
            return DoWhileFlowStep(condition=condition or "condition", body_steps=body_steps)

        def _extract_for_statement(self, for_ctx) -> ForInFlowStep:
            is_await = for_ctx.AWAIT() is not None
            header = context.compact(for_ctx.forLoopParts())
            body_steps = self._extract_statement_as_steps(for_ctx.statement())
            return ForInFlowStep(header=header or "item in collection", is_await=is_await, body_steps=body_steps)

        def _extract_switch_statement(self, switch_ctx) -> SwitchFlowStep:
            expression = context.compact(switch_ctx.expression())
            cases: list[SwitchCaseFlow] = []
            for case_ctx in (switch_ctx.switchStatementCase() or []):
                label = f"case {context.compact(case_ctx.guardedPattern())}"
                steps = self._extract_statements(case_ctx.statements())
                cases.append(SwitchCaseFlow(label=label, steps=steps))
            if switch_ctx.switchStatementDefault() is not None:
                steps = self._extract_statements(switch_ctx.switchStatementDefault().statements())
                cases.append(SwitchCaseFlow(label="default", steps=steps))
            return SwitchFlowStep(expression=expression, cases=tuple(cases))

        def _extract_try_statement(self, try_ctx) -> TryCatchFlowStep:
            body_steps = self._extract_block(try_ctx.block())
            catches: list[CatchClauseFlow] = []
            for on_part_ctx in (try_ctx.onPart() or []):
                if on_part_ctx.ON() is not None:
                    type_text = context.compact(on_part_ctx.typeNotVoid())
                    catch_part = on_part_ctx.catchPart()
                    if catch_part is not None:
                        var_text = context.compact(catch_part)
                        pattern = f"on {type_text} {var_text}"
                    else:
                        pattern = f"on {type_text}"
                elif on_part_ctx.catchPart() is not None:
                    pattern = context.compact(on_part_ctx.catchPart())
                else:
                    pattern = "catch"
                steps = self._extract_block(on_part_ctx.block())
                catches.append(CatchClauseFlow(pattern=pattern, steps=steps))
            finally_steps: tuple[ControlFlowStep, ...] = ()
            if try_ctx.finallyPart() is not None:
                finally_steps = self._extract_block(try_ctx.finallyPart().block())
            return TryCatchFlowStep(
                body_steps=body_steps,
                catches=tuple(catches),
                finally_steps=finally_steps,
            )

        # ── Utilities ───────────────────────────────────────────────────────

        def _with_container(self, name: str, callback):
            self._containers.append(name)
            try:
                return callback()
            finally:
                self._containers.pop()

    return DartControlFlowVisitor


def _name_from_class_name_maybe_primary(cnmp) -> str:
    """Extract the type name from a classNameMaybePrimary context."""
    if cnmp is None:
        return "class"
    twp = cnmp.typeWithParameters() if hasattr(cnmp, "typeWithParameters") else None
    if twp is not None:
        return twp.typeIdentifier().getText()
    pc = cnmp.primaryConstructor() if hasattr(cnmp, "primaryConstructor") else None
    if pc is not None:
        return pc.typeWithParameters().typeIdentifier().getText()
    return "class"
