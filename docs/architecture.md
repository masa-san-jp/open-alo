# Architecture

## Goal

Open ALO makes language-defined judgment workflows inspectable and executable without binding the workflow to one model vendor.

## Components

```text
              ALO source
                  │
                  ▼
            ┌───────────┐
            │ Validator │
            └─────┬─────┘
                  ▼
            ┌───────────┐
            │ Compiler  │
            └─────┬─────┘
                  ▼
              Graph IR
              /      \
             /        \
     Mermaid view    Runtime
                       │
               Decision Provider
              /       |        \
           Jev   OpenAI-compat  Mock
                       │
                  Rule Engine
                       │
                   Next State
                       │
                 Output + Run Log
```

## Source of truth

The ALO source and its canonical compiled Graph IR are the machine-readable sources of truth.

A Mermaid diagram is generated output. Editing a diagram must not silently alter executable behavior.

## Provider boundary

The provider answers semantic questions. It does not perform authoritative arithmetic, mutate ALO state, choose undeclared categories, define new workflow nodes at runtime, or silently change thresholds or rules.

The runtime owns deterministic behavior.

## Jev adapter

Jev is an optional adapter.

```text
binary       ↔ Noul
categorical  ↔ Choice
scalar       ↔ Score
```

This mapping keeps ALO files portable to other providers.

The repository includes a provisional `JevClient` protocol and `JevProvider`
adapter boundary. It is intentionally pending real Jev API access and is not
verified against the Jev service. No live Jev account is required to validate,
compile, test, or run an ALO with another provider; the Mock and
OpenAI-compatible providers remain fully sufficient for those workflows.

## Planned packages

```text
packages/core       schema + typed IR
packages/compiler   ALO → Graph IR
packages/runtime    graph execution + run records
packages/cli        alo validate/graph/run/test
packages/providers  provider adapters
studio              self-hostable visual UI
conformance         compatibility suite
```

## Local-first requirement

A conforming reference implementation should support a path where ALO validation, graph generation, and mock-provider tests work offline, and local model providers can run without a hosted Open ALO service.

Cloud services may be added as conveniences, never as protocol requirements.
