# Architecture

> This architecture implements the canonical ALO model in [spec.md](spec.md).  
> `mainObj / subObjList / State / managerObj` are the core. Graphs, Jev, rules engines, and providers are supporting mechanisms.

## 1. Layered architecture

```text
                  Authoring Layer
                       │
                 ALO Prompt / YAML
                       │
                       ▼
              Canonical ALO Model
       ┌───────────────┼────────────────┐
       │               │                │
    mainObj        subObjList          State
       └───────────────┬────────────────┘
                       │
                  managerObj
                       │
       ┌───────────────┼──────────────────┐
       │               │                  │
 deterministic      LLM work        Jev judgments
 calculation                           │
       └───────────────┬──────────────────┘
                       │
                 State transition
                       │
                     Output
```

## 2. Derived representations

The same canonical ALO model can produce multiple derived artifacts.

```text
Canonical ALO Model
    ├── canonical prompt
    ├── ALO diagram / Mermaid
    ├── execution plan
    ├── Jev requests
    ├── run record
    └── tests
```

No derived artifact is allowed to redefine the core ALO semantics.

## 3. ALO Diagram

The diagram compiler MUST first preserve object semantics:

```text
MAIN_OBJECT
  └─ CONTAINS → SUB_OBJECT*

MANAGER
  ├─ COORDINATES → MAIN_OBJECT / SUB_OBJECT*
  ├─ READS_STATE → STATE
  ├─ UPDATES_STATE → STATE
  ├─ RECEIVES ← INPUT
  └─ EMITS → OUTPUT
```

Execution details may then be overlaid:

```text
MANAGER
  ├─ CALLS → JEV_NOUL
  ├─ CALLS → JEV_CHOICE
  ├─ CALLS → JEV_SCORE
  ├─ CALLS → DETERMINISTIC_CALC
  └─ CALLS → EXTERNAL_TOOL
```

## 4. Jev adapter

Jev is an optional execution adapter used by manager operations.

It is not a peer replacement for ALO and not the canonical object model.

Jev results return to `managerObj`, which interprets them under the declared ALO behavior and state-update policy.

## 5. Runtime

The runtime implements manager execution.

Responsibilities:

- load the ALO definition;
- construct or restore State;
- render/provide the canonical prompt when an LLM is used;
- execute manager steps;
- call Jev or other tools when declared;
- apply deterministic calculations;
- apply explicit State transitions;
- emit output;
- persist a run trace.

## 6. Existing Draft 0.1 implementation

The current repository contains a working workflow-oriented runtime created from the superseded Draft 0.1 interpretation.

Useful components may be retained:

- YAML loading;
- schema validation infrastructure;
- deterministic expression/rule execution;
- provider adapters;
- Jev adapter;
- run records;
- Mermaid/SVG generation;
- CLI;
- Studio;
- packaging/conformance infrastructure.

However, these components MUST be refactored so the canonical data model preserves:

- `mainObj`;
- `subObjList`;
- `State`;
- `managerObj`.

The current `binary/categorical/scalar + transition_rules` representation may survive only as an execution submodel inside `managerObj`, not as the definition of ALO itself.
