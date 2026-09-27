# Open ALO

**Write. Visualize. Run.**

Open ALO is an open-source toolkit and specification for creating **Abstract Language Objects (ALO)**, visualizing them as explicit decision graphs, and executing them with **Jev or compatible decision providers**.

The goal:

> Anyone should be able to describe a decision workflow in language, inspect the resulting graph, run it reproducibly, fork it, and execute it locally without depending on a single vendor or hosted service.

## What Open ALO provides

```text
Natural-language intent
        ↓
      ALO
        ↓
 Validation / Compile
        ↓
    Graph IR
    ├── Mermaid diagram
    └── executable workflow
        ↓
Decision Provider
    ├── Jev
    ├── OpenAI-compatible models
    ├── local models
    └── mock/test provider
        ↓
Deterministic Rules
        ↓
 State transition / Output
```

Open ALO separates probabilistic judgment, deterministic computation, representation, visualization, and execution provider.

## Core principles

1. **Open specification** — ALO must be implementable without the reference runtime.
2. **Local-first** — hosted infrastructure must not be required.
3. **Provider-neutral** — Jev is supported, but ALO must not depend on Jev.
4. **Text-based artifacts** — ALO packages should remain readable, diffable, forkable, and Git-friendly.
5. **Graph as inspection surface** — diagrams are generated from the same source used for execution.
6. **Reproducibility** — inputs, versions, provider configuration, thresholds, rule traces, and outputs should be recordable.
7. **Testability** — decision nodes and deterministic rules are evaluated separately.
8. **No hidden state mutation** — providers return decisions; deterministic runtime code updates state.

## Decision model

| Open ALO type | Meaning | Jev mapping |
| --- | --- | --- |
| `binary` | yes/no probability | Noul |
| `categorical` | one option from a fixed set | Choice |
| `scalar` | degree or score on a defined scale | Score |

Jev is one **Decision Provider**, not the ALO specification itself.

## Repository layout

```text
open-alo/
├── README.md
├── docs/
│   ├── architecture.md
│   └── spec.md
├── examples/
│   └── minimal/
│       ├── alo.yaml
│       └── README.md
├── packages/          # reference implementation (planned)
│   ├── core/
│   ├── compiler/
│   ├── runtime/
│   ├── cli/
│   └── providers/
├── conformance/       # compatibility tests (planned)
└── studio/            # visual editor / graph viewer (planned)
```

## Minimal ALO

```yaml
alo:
  spec_version: "0.1"
  id: support-triage
  version: "0.1.0"
  purpose: Route a customer support request.

  inputs:
    message:
      type: string
      required: true

  state_schema:
    status:
      type: enum
      values: [new, routed]
      initial: new
      updated_by: rule_engine

  decisions:
    - id: is_emergency
      type: binary
      reads: [input.message]
      question: Is this request an emergency?

    - id: category
      type: categorical
      reads: [input.message]
      options:
        technical: Technical problem
        billing: Billing problem
        other: Other

  transition_rules:
    - id: route-emergency
      when: decision.is_emergency.p_true >= 0.90
      set:
        action: escalate

  outputs:
    action:
      type: string
```

## Intended CLI

```bash
alo validate examples/minimal/alo.yaml
alo graph examples/minimal/alo.yaml
alo run examples/minimal/alo.yaml --input input.json
alo test examples/minimal/
```

The CLI does not exist yet. These commands define the intended public interface.

## Jev

TypeSafe describes Jev as a model for typed probabilistic decisions inside software. Its published workflow examples decompose tasks into **Noul**, **Choice**, and **Score**, while keeping arithmetic, dates, and explicit rules in code.

Open ALO will support Jev through an adapter. A Jev account must never be required merely to read, validate, visualize, test, or run ALO with another provider.

- TypeSafe: https://typesafe.ai/
- Workflow examples: https://evals.typesafe.ai/

## Status

**Pre-alpha / specification-first.**

Current priorities:

1. Freeze the minimum ALO schema.
2. Define Graph IR.
3. Build schema validation.
4. Generate Mermaid deterministically.
5. Define the Decision Provider interface.
6. Add Jev and OpenAI-compatible adapters.
7. Implement the CLI.
8. Add conformance tests.
9. Build a self-hostable Studio.

## License

**TBD before the first tagged release.**

The project is intended to be openly usable, modifiable, redistributable, and self-hostable. The exact license will be selected explicitly rather than assumed.

---

## 日本語

Open ALOは、**ALOを書く → 図で確認する → Jevまたは互換Decision Providerで実行する**までを、特定サービスにロックインされず誰でも再現できるようにするOSSプロジェクトです。

ALOの仕様、Graph IR、Runtime、CLI、テスト仕様を公開し、最終的にはローカル環境だけでも実行可能にすることを目標とします。
