# Open ALO

*[日本語](README.md)*

[![Tests](https://github.com/masa-san-jp/open-alo/actions/workflows/tests.yml/badge.svg)](https://github.com/masa-san-jp/open-alo/actions/workflows/tests.yml)

**Write ALO. See ALO. Calculate with Jev.**

> **Canonical semantics: Draft 0.2**
>
> Open ALO's core model is **`mainObj + subObjList + State + managerObj`**.
> Earlier Draft 0.1 documentation incorrectly reduced ALO to a probabilistic workflow DSL. See [Implementation Correction](docs/implementation-correction.md).

## What is an ALO

An ALO (Abstract Language Object) is a way of structuring a real-world concept, system, role, or dynamic state as a **language object** an LLM can operate on.

An ALO has four core components:

| Component | Role |
| --- | --- |
| `mainObj` | the top-level object representing the whole ALO |
| `subObjList` | the child objects that compose `mainObj` |
| `State` | the ALO's dynamic state |
| `managerObj` | the executing agent that interprets input, coordinates objects, updates State, and produces output |

```text
Write the ALO
   ↓
ALO Prompt
   ↓
Canonical ALO Model
   ├────────────→ ALO Diagram
   │
   └────────────→ execute managerObj
                        │
             ┌──────────┼──────────┐
             │          │          │
           LLM      plain code    Jev
                                   │
                        Noul / Choice / Score
                                   │
                                   ▼
                              managerObj
                                   │
                             State update
                                   │
                                 Output
```

## Important: Jev is not ALO

Jev is an **optional execution mechanism** that `managerObj` may use to compute an ambiguous judgment. Jev's `Noul / Choice / Score` never replace `mainObj / subObjList / State / managerObj`.

## ALO Diagram

The ALO Diagram visualizes an ALO's conceptual structure. At minimum, it represents the relationships between mainObj, subObjList, State, managerObj, Input, and Output, and it may overlay Jev or plain-code calculation nodes when relevant.

## Minimal ALO

A correct minimal example lives at [examples/canonical-minimal/](examples/canonical-minimal/).

```yaml
alo:
  spec_version: "0.2"
  id: learning-coach
  version: "0.1.0"

  mainObj:
    id: learning_coach
    purpose: 学習者を支援する

  subObjList:
    - id: comprehension_analyzer
      purpose: 理解度を評価する
    - id: explanation_engine
      purpose: 状態に応じた説明を作る

  State:
    level:
      type: integer
      value: 1
    progress:
      type: number
      value: 0.0
    activeStatus:
      type: string
      value: initializing

  managerObj:
    id: learning_coach_manager
    input:
      - user_message
    process:
      - id: read_input
        action: 入力とStateを読む
      - id: analyze
        action: comprehension_analyzerで理解度を評価する
        calculation:
          provider: optional
          jev:
            type: Noul
            question: 学習者は対象概念を実質的に理解しているか
      - id: respond
        action: explanation_engineで状態に応じた応答を作る
    output:
      - response
```

(This YAML validates as-is with `alo validate`. See the next section for how to run it.)

## Install and run

```bash
git clone https://github.com/masa-san-jp/open-alo.git
cd open-alo
```

Requires Python 3.10 or newer. The reference implementation runs on the standard library alone; `pip install` is not strictly required. If you use YAML input, `pip install pyyaml` is recommended (without it, a Ruby fallback is used for YAML if Ruby is available; JSON input needs no extra dependency at all).

The project is not packaged yet, so the `alo` command is invoked via `python3 -m packages.cli`.

```bash
python3 -m packages.cli validate examples/canonical-minimal/alo.yaml
python3 -m packages.cli prompt   examples/canonical-minimal/alo.yaml
python3 -m packages.cli graph    examples/canonical-minimal/alo.yaml
python3 -m packages.cli test     examples/canonical-minimal
```

Run the full test suite with:

```bash
python3 -m unittest discover -s tests
```

## Shortest path for an implementing agent

**Read this first:** [docs/complete-implementation-guide.md](docs/complete-implementation-guide.md)

This single file covers the definition of ALO, its four components, the ALO Prompt, the ALO Diagram, where Jev fits in, the Runtime, State updates, reproducibility, the Draft 0.1 mistake, implementation order, and completion criteria.

## Reading order for the specification

1. [docs/spec.md](docs/spec.md) — **the normative SSOT for ALO itself**
2. [docs/architecture.md](docs/architecture.md) — the structure for implementing ALO as a tool
3. [docs/implementation-correction.md](docs/implementation-correction.md) — what was corrected from Draft 0.1
4. [examples/canonical-minimal/](examples/canonical-minimal/) — the minimal correct ALO
5. the individual Jev / Graph / Runtime specifications

## About the current implementation

The Runtime, Graph, schema, examples, and conformance fixtures based on the superseded Draft 0.1 interpretation (ALO as a probabilistic workflow DSL) have been removed (see `docs/implementation-correction.md`). The provider, CLI, and packaging shells were not Draft-0.1-specific, so they were reused as-is for the canonical model. The web UI (Studio) was removed because it was never something the user actually wanted -- use is expected to be a coding agent driving the CLI (`alo validate/prompt/graph/run/test`) directly.

When code conflicts with the specification, `docs/spec.md` wins and the code gets fixed.

## Goal

Open ALO aims to be an OSS project where anyone can write an ALO, use it as a prompt, diagram it, use Jev for managerObj's judgments, record and reproduce runs, run everything locally, and fork, modify, and share it freely.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)

## Status

**Pre-alpha / semantic correction in progress.**

See [ROADMAP.md](ROADMAP.md).
