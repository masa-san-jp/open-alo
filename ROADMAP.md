# Roadmap

## P0 — Correct the ALO semantic model

The first implementation pass used a superseded interpretation where ALO was treated primarily as a probabilistic workflow DSL.

Before further feature work, the implementation must conform to `docs/spec.md` Draft 0.2.

- [ ] schema represents `mainObj`
- [ ] schema represents `subObjList`
- [ ] schema represents `State`
- [ ] schema represents `managerObj`
- [ ] canonical prompt renderer preserves all four components
- [ ] Graph IR represents the ALO object model
- [ ] Mermaid/SVG diagrams show object structure plus execution overlay
- [ ] runtime executes managerObj semantics
- [ ] Jev is invoked only as an optional manager calculation/judgment mechanism
- [ ] conformance tests reject implementations that lose the four core components
- [ ] minimal example demonstrates Prompt → ALO Diagram → Jev calculation → State update

See: `docs/implementation-correction.md`.

## Existing implementation — reusable infrastructure, not canonical semantics

The repository already contains working infrastructure for:

- schema validation
- parsing
- workflow-oriented Graph IR
- Mermaid/SVG generation
- Decision Providers
- Jev adapter
- OpenAI-compatible adapter
- deterministic rules
- run records/replay
- CLI
- conformance harness
- Studio
- packaging/registry

These components should be migrated rather than discarded where practical.

## P1 — Reproducible ALO authoring

- [ ] natural-language authoring template
- [ ] structured YAML/JSON serialization
- [ ] deterministic canonical prompt rendering
- [ ] versioned object definitions
- [ ] explicit dynamic sub-object creation records

## P2 — ALO visualization

- [ ] object-structure diagram
- [ ] state relationships
- [ ] manager flow
- [ ] optional execution/Jev overlay
- [ ] stable Mermaid and SVG output

## P3 — Jev calculation

- [ ] manager operation → Noul
- [ ] manager operation → Choice
- [ ] manager operation → Score
- [ ] normalized result recording
- [ ] deterministic update rules
- [ ] offline/mock equivalent for testing

## P4 — Accessibility and ecosystem

- [ ] CLI workflows
- [ ] self-hostable Studio
- [ ] plain-file import/export
- [ ] package format
- [ ] Git repository install
- [ ] optional discovery registry
- [ ] AEP governance
