# Darta

Darta parses Dart source code through ANTLR and renders Nassi-Shneiderman diagrams as single-file HTML pages. The architecture is DDD-inspired with hexagonal boundaries so the ANTLR infrastructure stays behind ports and the domain layer stays independent.

## Feature Matrix

### Control Flow

| Construct | Extracted | Diagram |
|---|---|---|
| `if` / `else if` / `else` | ✅ | ✅ NS triangle with Yes/No branches |
| `if (x case Pattern when guard)` Dart 3 | ✅ | ✅ full pattern+guard in condition |
| `while` | ✅ | ✅ loop block |
| `do … while` | ✅ | ✅ body-first loop block |
| `for (init; cond; incr)` | ✅ | ✅ for block |
| `for (x in collection)` | ✅ | ✅ for block |
| `await for (x in stream)` | ✅ | ✅ purple accent + "Await for" header |
| `switch / case / default` (classic) | ✅ | ✅ side-by-side columns |
| `switch` with Dart 3 patterns & guards | ✅ | ✅ pattern text in case label |
| `switch(v) { p => e }` expression (Dart 3) | ✅ | ✅ teal accent + switch badge |
| `try / on / catch / finally` | ✅ | ✅ catch lanes + finally |
| `throw expr` | ✅ | ✅ red accent + `throw` badge |
| `await expr` | ✅ | ✅ purple accent + `await` badge |
| `yield` / `yield*` | ✅ | ✅ green accent + `yield` / `yield*` badge |
| `return expr` | ✅ | ✅ teal accent + `return` badge |
| `rethrow` | ✅ | ✅ red accent + `rethrow` badge |
| `assert(cond, msg?)` | ✅ | ✅ amber accent + `assert` badge |
| `break` / `break label` | ✅ | ✅ orange accent + `break` badge |
| `continue` / `continue label` | ✅ | ✅ orange accent + `continue` badge |
| `var (a, b) = expr` pattern variable | ✅ | ✅ blue accent + pattern destructuring |

### Function Discovery

| Kind | Discovered | Notes |
|---|---|---|
| Top-level function | ✅ | |
| Top-level getter | ✅ | |
| Top-level setter | ✅ | |
| Class method | ✅ | static, instance, abstract, and external declarations |
| Class getter | ✅ | concrete and abstract/external declarations |
| Class setter | ✅ | concrete and abstract/external declarations |
| Constructor (default) | ✅ | block-body and semicolon forms |
| Constructor (named) | ✅ | block-body and semicolon forms |
| Constructor (redirecting `this(...)`) | ✅ | discovered structurally; no function body to diagram |
| Constructor (`const`) | ✅ | discovered structurally |
| Redirecting factory (`= ClassName`) | ✅ | discovered structurally; no function body to diagram |
| Factory constructor | ✅ | block-body and redirecting forms |
| Operator overload | ✅ | |
| Mixin method / getter | ✅ | |
| Extension method / getter | ✅ | |
| Extension type method | ✅ | |
| Enum method / getter | ✅ | via `enumBody` member declarations |
| Local function declaration | ⬜ | shown as action label |

### Grammar

| Feature | Status |
|---|---|
| Grammar source | ✅ `dart-lang/sdk` spec parser v0.60 |
| Dart 2 syntax | ✅ |
| Dart 3 patterns & records | ✅ |
| Dart 3 sealed / base / final classes | ✅ parsed, not specially rendered |
| String interpolation | ✅ lexer brace-stack |
| `async` / `async*` / `sync*` functions | ✅ |

### Rendering

| Feature | Status |
|---|---|
| Single-file HTML output | ✅ inline CSS/markup; default theme requests Google Fonts |
| Dark Tokyo Night theme | ✅ |
| JetBrains Mono font | ✅ via Google Fonts |
| Depth-coded nested ifs (50 levels) | ✅ color cycling + Unicode badges ①–㊿ |
| Switch — side-by-side columns | ✅ |
| `await` purple accent | ✅ |
| Responsive layout | ✅ |
| Directory index page | ✅ |

---

## Screenshots

**Basic control flow** — sequential actions and an if-block with Yes/No branches:

![Basic NS diagram](docs/screenshots/nassi_diagram.png)

**Deeper nesting and extracted members** — getters and nested conditionals rendered as first-class diagram entries:

![Named constructors and getters](docs/screenshots/nested_depth.png)

---

## Quick Start

1. Install dependencies:

```bash
uv sync --extra dev
```

2. Generate the Dart parser from the vendored grammar:

```bash
uv run python scripts/generate_dart_parser.py
```

3. Build a Nassi-Shneiderman diagram for one Dart file:

```bash
uv run darta nassi-file path/to/file.dart --out output/file.nassi.html
```

4. Build diagrams for an entire directory:

```bash
uv run darta nassi-dir path/to/project --out output/nassi-bundle
```

5. Parse a file and get a JSON structural report:

```bash
uv run darta parse-file path/to/file.dart
```

See `examples/feature_tour.dart` for a single file that exercises every supported construct.

---

## Architecture

Four explicit layers:

| Layer | Responsibility |
|---|---|
| `domain` | model, invariants, ports, domain events |
| `application` | use cases, DTOs |
| `infrastructure` | ANTLR adapter, filesystem, event publishing |
| `presentation` | CLI |

---

## Roadmap

### Near-term

- 🔁 **Local function inlining** — expand nested `void helper() {}` bodies inline in parent diagram

### Medium-term

- 🌊 **Cascade operator** (`..`) — chain steps grouped into a single block
- 🗂️ **Symbol graph export** — JSON graph of all types, methods, and their relationships
- 🖼️ **SVG / PNG export** — headless Chrome or `playwright` render pass
- 🎨 **Pattern destructuring visual** — show structure of pattern matches in if/switch

### Long-term

- ⚡ **Incremental parsing** — re-parse only changed files in a directory run
- 🔍 **Semantic passes** — type resolution, call graph, dead code hints on top of the structural model
- 🌐 **VS Code extension** — live NSD preview panel alongside the editor
- 📊 **Complexity metrics** — cyclomatic complexity and nesting depth badges per function
