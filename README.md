# Darta

Darta parses Dart source code through ANTLR and renders Nassi-Shneiderman diagrams as self-contained HTML pages. The architecture is DDD-inspired with hexagonal boundaries so the ANTLR infrastructure stays behind ports and the domain layer stays independent.

## Feature Matrix

### Control Flow

| Construct | Extracted | Diagram |
|---|---|---|
| `if` / `else if` / `else` | ✅ | ✅ NS triangle with Yes/No branches |
| `if (x case Pattern when guard)` Dart 3 | ✅ | ✅ condition shows full pattern |
| `while` | ✅ | ✅ loop block |
| `do … while` | ✅ | ✅ body-first loop block |
| `for (init; cond; incr)` | ✅ | ✅ for block |
| `for (x in collection)` | ✅ | ✅ for block |
| `switch / case / default` (classic) | ✅ | ✅ side-by-side columns |
| `switch` with Dart 3 patterns & guards | ✅ | ✅ pattern text in case label |
| `try / on / catch / finally` | ✅ | ✅ catch lanes + finally |
| `await expr` | ✅ | ✅ purple accent + `await` badge |
| `yield` / `yield*` | ✅ | ⬜ plain action (no special style) |
| `rethrow` | ✅ | ⬜ plain action |
| `assert(cond)` | ✅ | ⬜ plain action |
| `break label` / `continue label` | ✅ | ⬜ plain action |

### Function Discovery

| Kind | Discovered | Notes |
|---|---|---|
| Top-level function | ✅ | |
| Top-level getter | ✅ | |
| Top-level setter | ✅ | |
| Class method | ✅ | static and instance |
| Class getter | ✅ | |
| Class setter | ✅ | |
| Constructor (default) | ✅ | block body only |
| Constructor (named) | ✅ | block body only |
| Factory constructor | ✅ | |
| Operator overload | ✅ | |
| Mixin method / getter | ✅ | |
| Extension method / getter | ✅ | |
| Extension type method | ✅ | |
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
| Self-contained HTML output | ✅ no external dependencies |
| Dark Tokyo Night theme | ✅ |
| JetBrains Mono font | ✅ via Google Fonts |
| Depth-coded nested ifs (50 levels) | ✅ color cycling + Unicode badges ①–㊿ |
| Switch — side-by-side columns | ✅ |
| `await` purple accent | ✅ |
| Responsive layout | ✅ |
| Directory index page | ✅ |

---

## Screenshots

**`session_cipher.dart`** — constructor entry, sequential actions, and an if-block with Yes/No branches:

![Basic NS diagram](docs/screenshots/nassi_diagram.png)

**`session_state.dart`** — named constructors and getters extracted as first-class diagram entries:

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

- 🎨 **Styled `yield` / `assert` / `rethrow` steps** — distinctive block types instead of plain action boxes
- 🔁 **Local function recursion** — inline nested `void helper() {}` bodies into the parent diagram
- 🏷️ **`break label` / `continue label`** — render as structured jump annotations on loop blocks
- 📦 **`switch` expression** — Dart 3 `final x = switch(v) { ... }` as an inline expression step

### Medium-term

- 🌊 **Cascade operator** (`..`) — chain steps grouped into a single block
- 🔀 **Pattern binding annotations** — show bound variable names in pattern-matching steps
- 🗂️ **Symbol graph export** — JSON graph of all types, methods, and their relationships
- 🖼️ **SVG / PNG export** — headless Chrome or `playwright` render pass

### Long-term

- ⚡ **Incremental parsing** — re-parse only changed files in a directory run
- 🔍 **Semantic passes** — type resolution, call graph, dead code hints on top of the structural model
- 🌐 **VS Code extension** — live NSD preview panel alongside the editor
- 📊 **Complexity metrics** — cyclomatic complexity and nesting depth badges per function
