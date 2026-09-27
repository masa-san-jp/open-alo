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

## 6. What was corrected

The first implementation pass (Draft 0.1) built a working
`binary/categorical/scalar + transition_rules` workflow runtime as if that
were the definition of ALO. It was not: see
`docs/implementation-correction.md`. That code, its schema
(`schemas/alo.schema.json`), its example (`examples/minimal/`), and its
conformance fixtures (`conformance/cases/`) have been removed rather than
kept as a migration path.

Components that were already provider-neutral, not tied to the workflow-DSL
shape, were kept and now serve the canonical model directly: YAML/JSON
loading, provider adapters (including the Jev adapter), the deterministic
expression evaluator (now used for `managerObj.state_updates[].when`),
Mermaid/SVG generation (which renders any `{nodes, edges}` graph, including
Object Graph IR), the CLI, Studio, and packaging shells.

The `binary/categorical/scalar + transition_rules` representation itself
survives only where it belongs: as one possible execution submodel a
`managerObj.process` step's `calculation` may invoke (see
`packages/providers/`), never as the definition of ALO.
