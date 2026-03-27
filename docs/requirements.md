# Requirements

## Functional Requirements

### Parse Report Capabilities

1. The system must parse a single `.dart` file.
2. The system must parse a directory recursively and ignore non-Dart files.
3. The system must return a versioned parse report for each source unit.
4. The system must aggregate file-level outcomes into one parsing job result.
5. The system must capture syntax diagnostics with message, severity, line, and column.
6. The system must continue parsing other files when one file fails.
7. The system must extract a stable structural model containing at least imports, type aliases, classes, enums, mixins, extensions, functions, variables, and constants.
8. The system must expose grammar version and report schema version as part of the result contract.
9. The system must distinguish successful parsing, parsing with diagnostics, and technical failure.
10. The CLI must return machine-readable JSON for parse workflows.

### Control Flow and Diagram Capabilities

11. The system must extract structured control flow for each function-like member with a body in a Dart source file.
12. The control-flow model must support `if/else`, `while`, `do/while`, `for`, `for-in`, `await for`, classic `switch`, switch expressions, and `try/on/catch/finally`.
13. The extractor must preserve Dart 3 pattern and guard text where possible in conditions and switch cases.
14. The model must represent statement-level constructs such as `throw`, `await`, `yield`, `yield*`, `return`, `rethrow`, `assert`, `break`, `continue`, and pattern variable declarations.
15. The system must build an HTML Nassi-Shneiderman diagram for a single Dart file.
16. The system must build a directory bundle of Nassi diagrams and an index page that links to each generated document.
17. Diagram metadata must expose source location, function count, and function names.
18. Diagram rendering must preserve function signatures and qualified names.
19. Nested conditional rendering must remain readable up to the supported depth range and expose depth cues in the HTML output.
20. The CLI must return machine-readable JSON metadata for diagram generation workflows.

### Architectural and Contract Requirements

21. External dependencies must stay behind explicit ports.
22. Delivery concerns such as filesystem output paths, CLI arguments, and JSON formatting must remain outside the domain layer.
23. Parser limitations must be visible to consumers rather than silently presented as compiler-level certainty.
24. The system must keep generated parser code isolated from the core domain and application logic.

## Non-Functional Requirements

### Maintainability

* keep domain and application layers independent from ANTLR, filesystem, HTML rendering, and CLI code
* keep modules small and single-purpose where practical, and keep complexity isolated when large visitors or renderers are unavoidable
* use explicit contracts and constructor injection
* keep parse-report and diagram workflows understandable as separate application services

### Testability

* cover domain rules with unit tests
* cover parser and extractor behavior with boundary tests
* test renderer output at the HTML and CSS contract level when layout regressions are likely
* keep use cases runnable with test doubles

### Operability

* emit structured lifecycle logs for parse workflows
* make errors explicit and machine-readable
* support deterministic CLI execution in CI
* keep output paths predictable for generated diagram files and bundles

### Resilience

* isolate file failures from the rest of a parse job
* distinguish business validation failures from technical failures
* avoid partial job completion states that look successful
* keep control-flow extraction and rendering failures explicit instead of silently dropping content

### Rendering Quality

* generated diagrams must remain legible on common desktop widths
* nested branches must wrap within the function canvas instead of forcing every nested node to widen the whole diagram
* long labels and signatures must wrap instead of overflowing their containers

### Security

* do not execute parsed source
* avoid hidden network calls during normal parsing or diagram generation, except for optional browser font requests in the default theme
* treat the filesystem as an input/output boundary, not a trust boundary

### Extensibility

* allow new adapters without changing stable domain code
* allow richer structural extraction behind the same use-case contract
* allow new renderers to consume `ControlFlowDiagram` without changing extraction logic
* keep schema and grammar versions explicit for backward-compatible evolution

## Constraints and Honesty

The current parser is based on the Dart SDK spec grammar (`dart-lang/sdk`, spec parser v0.60) and a small scripted compatibility patch for Python target generation. The system is expected to be honest about ambiguity, unsupported syntax, or grammar drift. When the tool cannot provide analyzer-grade certainty, the contract should surface that limitation rather than hide it.

## Quality Attributes

The system prioritizes clarity, correctness, and evolvability over premature optimization. Performance optimization is allowed only after measurement and must preserve architectural boundaries, contract clarity, and diagram readability.
