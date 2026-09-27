# Implementation Correction: Draft 0.1 → Canonical ALO Draft 0.2

## Why this correction exists

The first Open ALO implementation incorrectly interpreted ALO primarily as a probabilistic decision workflow:

```text
Input → Decision → Rule → State → Output
```

That was too narrow.

The original ALO model is:

```text
mainObj
+ subObjList
+ State
+ managerObj
```

with natural-language prompting and dynamic object/state management as core semantics.

The workflow machinery should implement parts of `managerObj`; it should not replace the ALO object model.

## What is wrong in the current implementation

The current Draft 0.1 schema and runtime make these concepts absent or non-normative:

- `mainObj`
- `subObjList`
- `managerObj`

As a result, an implementation agent reading the repository can build a valid Draft 0.1 workflow engine while still not implementing ALO.

## What can be kept

The following work is potentially reusable:

- loader/validator framework;
- canonical serialization utilities;
- graph rendering infrastructure;
- CLI framework;
- deterministic expression and rule engine;
- provider abstraction;
- Jev adapter;
- OpenAI-compatible adapter;
- run records;
- tests/conformance harness;
- Studio shell;
- packaging and registry utilities.

## What must change

### Schema

The root schema must represent the four canonical components.

### Compiler

The compiler must preserve the object model before generating execution nodes.

### Graph

Graph IR must contain object-structure nodes and relationships, not only execution nodes.

### Runtime

Runtime must execute `managerObj`, including coordination of sub-objects and State.

### Jev

Jev calls must be manager operations. Jev primitives must not define the ALO object model.

### Studio

Studio must let a user see/edit:

- mainObj;
- subObjList;
- State;
- managerObj;
- the derived ALO diagram;
- optional Jev calculation nodes.

## Migration principle

Do not throw away working infrastructure unnecessarily.

Refactor this:

```text
ALO = workflow DSL
```

into this:

```text
ALO = object model

managerObj execution
    └── may compile to workflow operations
            ├── deterministic rules
            └── Jev decisions
```

## Blocking rule

Until core conformance is restored, new features SHOULD NOT extend the Draft 0.1 object model as though it were canonical.
