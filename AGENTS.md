# AGENTS.md — Open ALO implementation instructions

**Mandatory first read:** `docs/complete-implementation-guide.md`

## Read this before changing code

Open ALO's first implementation pass (Draft 0.1) incorrectly treated ALO
primarily as a probabilistic workflow DSL. That code, its schema, its
examples, and its conformance fixtures have been removed (see
`docs/implementation-correction.md`) rather than kept as a migration path.

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

## Writing a new ALO

When asked to turn a plain-language description into an ALO, write it
yourself, with your own reasoning -- do not call out to an external LLM API
for this. You are already the reasoning engine; this repository's schema
and examples are the harness that shapes what you write, not a service you
invoke. Producing an ALO does not require network access, an API key, or a
Decision Provider.

1. Read `docs/spec.md` and `schemas/alo-0.2.schema.json`, and look at
   `examples/canonical-minimal/alo.yaml` for a worked example.
2. Write the YAML directly: `mainObj` (id, purpose, responsibilities),
   `subObjList` (each with id and purpose), `State` (each key with a `type`
   and a `value`), and `managerObj` (`input`, `process` steps each with an
   `id` and an `action`, `output`). A process step may declare
   `calculation: {jev: {type: Noul|Choice|Score, question: ...}}` for a
   judgment it delegates to Jev -- see "Jev" above.
3. Iterate with the CLI until it is correct:

   ```bash
   alo validate <path>   # fix reported errors until this passes
   alo prompt <path>     # inspect the rendered ALO Prompt
   alo graph <path>      # inspect the compiled Object Graph IR as a diagram
   ```

4. Hand back all three as the deliverable: the ALO file itself, its
   diagram (`alo graph`'s output), and, if it declares Jev calculations,
   note that `JevProvider` needs no ALO-specific code to execute them (see
   `packages/providers/jev.py`) -- nothing further to generate.

`alo run <path> --input <input>.json --responses <responses>.json` (the
Mock Decision Provider) exists only for testing an ALO's `managerObj`
calculations once it is written; it is not part of authoring the ALO
itself.

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

## What was kept, and what was removed

Kept and reused directly by the canonical model (these were already
provider-neutral, not tied to the workflow-DSL shape):

- loaders (`packages/core`)
- provider adapters, including the Jev adapter (`packages/providers`)
- the safe expression evaluator, used for `state_updates[].when`
  (`packages/runtime/expressions.py`)
- the CLI, Studio, and packaging shells (`packages/cli`, `packages/studio`,
  `packages/packaging`)
- Mermaid/SVG rendering (`packages/compiler/mermaid.py`, `svg.py`) --
  reused as-is for Object Graph IR, since both operate generically on any
  `{nodes, edges}` graph

Removed rather than kept as a migration path, since they represented the
superseded Draft 0.1 workflow-DSL model, not canonical ALO semantics:
`schemas/alo.schema.json`, `packages/compiler/compiler.py`,
`packages/runtime/engine.py` and `replay.py`, `examples/minimal/`,
`conformance/cases/`, and the natural-language authoring assistant
(`packages/studio/assistant.py`, `/api/assist`) -- authoring an ALO is done
by the calling agent's own reasoning (see "Writing a new ALO" above), not
by calling an external LLM API.

## Status

P0 tracking issue #9 is resolved: every checklist item in `ROADMAP.md` is
checked. `docs/implementation-correction.md` and
`docs/complete-implementation-guide.md` remain the record of what was wrong
and why -- read them for history, but do not treat their "still in
progress" framing as current.
