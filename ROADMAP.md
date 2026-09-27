# Roadmap

## P0 — Correct the ALO semantic model

The first implementation pass used a superseded interpretation where ALO was treated primarily as a probabilistic workflow DSL.

Before further feature work, the implementation must conform to `docs/spec.md` Draft 0.2.

- [x] schema represents `mainObj`
- [x] schema represents `subObjList`
- [x] schema represents `State`
- [x] schema represents `managerObj`
- [x] canonical prompt renderer preserves all four components
- [x] Graph IR represents the ALO object model
- [x] Mermaid/SVG diagrams show object structure plus execution overlay
- [x] runtime executes managerObj semantics
- [x] Jev is invoked only as an optional manager calculation/judgment mechanism
- [x] conformance tests reject implementations that lose the four core components
- [x] minimal example demonstrates Prompt → ALO Diagram → Jev calculation → State update

See: `docs/implementation-correction.md`.

The superseded Draft 0.1 workflow DSL (schema, compiler, runtime, examples,
conformance fixtures, and the natural-language authoring assistant that
called an external LLM API to draft it) has been removed rather than kept
as a migration path -- it did not represent canonical ALO semantics, and
keeping it around risked confusing future readers about which model is
correct. Reusable infrastructure that was already provider-neutral and not
tied to the workflow-DSL shape (loaders, provider adapters, the Jev adapter,
the expression evaluator, the CLI/Studio/packaging shells) was kept and is
now used by the canonical model directly.

## P1 — Reproducible ALO authoring

- [x] natural-language authoring template (docs/spec.md section 5; rendered by `render_prompt`)
- [x] structured YAML/JSON serialization (`schemas/alo-0.2.schema.json`, `examples/canonical-minimal/`)
- [x] deterministic canonical prompt rendering (`render_prompt`; tested deterministic)
- [x] versioned object definitions (optional `version` on `mainObj`/each `subObjList` entry; recorded in the Run Record's `alo.object_versions` and in Object Graph IR node data)
- [x] explicit dynamic sub-object creation records (`creates_sub_obj` step field -> `dynamic_sub_obj_creations` in the Run Record; never silently mutates `alo.subObjList`)

## P2 — ALO visualization

- [x] object-structure diagram (`compile_object_graph`: MAIN_OBJECT/SUB_OBJECT/STATE/MANAGER/INPUT/OUTPUT)
- [x] state relationships (READS_STATE/UPDATES_STATE edges)
- [x] manager flow (RECEIVES/COORDINATES/EMITS edges, `manager_trace`)
- [x] optional execution/Jev overlay (JEV_NOUL/JEV_CHOICE/JEV_SCORE nodes, CALCULATES edges)
- [x] stable Mermaid and SVG output (deterministic; tested)

## P3 — Jev calculation

- [x] manager operation → Noul
- [x] manager operation → Choice
- [x] manager operation → Score
- [x] normalized result recording (via the existing `normalize_binary/categorical/scalar`, unchanged)
- [x] deterministic update rules (`state_updates` with optional `when`, evaluated by the existing safe expression evaluator)
- [x] offline/mock equivalent for testing (`MockDecisionProvider`; the ALO runs even with no provider configured when Jev is marked optional)

## P4 — Accessibility and ecosystem

- [x] CLI workflows (`alo validate/prompt/graph/run/test` all operate on the canonical model)
- [x] self-hostable Studio (`/api/prompt`, `/api/graph`, `/api/run` all operate on the canonical model)
- [x] plain-file import/export (pre-existing, client-side; unaffected by this correction)
- [x] package format (pre-existing `alo package build/install`; verified unchanged against a canonical 0.2 ALO)
- [x] Git repository install (pre-existing, unaffected)
- [x] optional discovery registry (pre-existing, unaffected)
- [x] AEP governance (pre-existing, unaffected)
