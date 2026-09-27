# AGENTS.md — Open ALO implementation instructions

## Read this before changing code

Open ALO is currently correcting a semantic mistake introduced in Draft 0.1.

### Canonical ALO

An ALO is defined by these four core concepts:

1. `mainObj`
2. `subObjList`
3. `State`
4. `managerObj`

This is non-negotiable unless the normative specification is deliberately changed through governance.

## Source-of-truth order

When sources conflict, use this order:

1. `docs/spec.md` — normative ALO semantics
2. `docs/architecture.md`
3. `docs/implementation-correction.md`
4. `examples/canonical-minimal/`
5. current roadmap / active P0 issues
6. existing code
7. existing tests
8. superseded Draft 0.1 issues/docs

Existing code and tests are NOT authoritative when they conflict with the canonical specification.

## Historical warning

Draft 0.1 incorrectly treated ALO primarily as:

```text
Input → Decision → Rule → State → Output
```

That model may be useful as an execution submodel of `managerObj`, but it is not the definition of ALO.

Do not preserve Draft 0.1 semantics merely because current tests pass.

## Jev

Jev is optional execution machinery used by `managerObj` for typed probabilistic judgments.

Allowed interpretation:

```text
managerObj
  └── calls Jev
        ├── Noul
        ├── Choice
        └── Score
```

Disallowed interpretation:

```text
ALO = Noul + Choice + Score + rules
```

Jev must not replace `mainObj`, `subObjList`, `State`, or `managerObj`.

## ALO diagram

A complete ALO diagram must be capable of representing at least:

- MAIN_OBJECT
- SUB_OBJECT
- STATE
- MANAGER
- INPUT
- OUTPUT

Execution overlays may additionally contain Jev, rule, calculation, or tool nodes.

A decision-only DAG is not a complete ALO diagram.

## State

Conceptually, `managerObj` owns State evolution.

A deterministic runtime/rule engine may mechanically apply explicit updates on behalf of managerObj.

Do not allow a provider adapter to silently mutate State.

## Prompt

Open ALO must support a language/prompt representation where the four core concepts remain visible and interpretable by an LLM.

A YAML/JSON serialization is tooling infrastructure. It must preserve, not erase, the language-object semantics.

## Implementation rule

Before marking work complete, verify that the implementation still answers all of these:

- Where is mainObj represented?
- Where are sub-objects represented?
- Where is State represented?
- Where is managerObj represented?
- How are their relationships represented?
- How is the canonical prompt produced?
- How is the ALO diagram produced?
- Where can managerObj call Jev?
- How is State changed and recorded?

If any answer is "it is represented implicitly by the decision workflow", the implementation is not conformant.

## Migration approach

Reuse working infrastructure where practical:

- loaders
- validation framework
- CLI shell
- graph rendering
- rule/expression engine
- provider adapters
- Jev adapter
- run records/replay
- Studio shell
- packaging
- test harness

Refactor the data model and semantics underneath them.

## Active correction

P0 tracking issue: #9.
