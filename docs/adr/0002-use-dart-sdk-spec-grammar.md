# ADR 0002: Use the Dart SDK spec grammar as the initial parsing engine

## Status

Accepted

## Context

The business needs a working Dart parser without building a grammar from scratch. The Dart SDK repository publishes the language spec grammar, and Darta already vendors that grammar in `resources/grammars/dart3/Dart.g`.

## Decision

Use the Dart SDK spec grammar (`dart-lang/sdk`, spec parser v0.60) as the initial grammar source and generate a Python parser through ANTLR 4.13.2 with a reproducible compatibility patch step for Python target generation.

## Consequences

Positive:

* faster delivery
* transparent source of truth
* easier future grammar updates
* compatibility fixes stay scripted instead of becoming undocumented manual edits

Negative:

* spec grammar behavior can still diverge from analyzer or compiler behavior
* Python target generation is not plug-and-play because upstream support code is Java-oriented
* the compatibility patch script becomes part of the supported toolchain
* downstream consumers must treat grammar version as an explicit compatibility concern
