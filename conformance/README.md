# Conformance fixtures

`cases/` holds the superseded Draft 0.1 workflow-DSL fixtures (kept only for
migration/testing of that legacy code path -- see AGENTS.md and
`docs/implementation-correction.md`; not canonical).

`canonical-cases/` holds the canonical Draft 0.2 object-model fixtures
(mainObj/subObjList/State/managerObj). Per docs/complete-implementation-guide.md
section 19, a conformant implementation must be unable to lose any of the
four core components; each case pins:

- `alo.yaml` -- the canonical source;
- `object_graph.json` -- the compiled Object Graph IR
  (`packages.compiler.compile_object_graph`), which must contain all of
  `MAIN_OBJECT`, `SUB_OBJECT`, `STATE`, `MANAGER`, `INPUT`, `OUTPUT`;
  a decision-only graph does not satisfy this fixture;
  (`packages.compiler.graph_to_json`);
- `prompt.md` -- the rendered ALO Prompt (`packages.compiler.render_prompt`),
  which must show all four components as their own sections;
- `runs/<run-name>/{input.json, responses.json, expected_run_record.json}` --
  a Mock-Decision-Provider run (`packages.runtime.run_manager`).

Golden Run Record comparisons intentionally exclude only `run_id` and
`timestamp` (inherently non-deterministic per run, including inside the
nested `alo` object for `canonical-cases`); every other field, including
`alo.canonical_hash`, is part of the pinned behavior and remains comparable.
