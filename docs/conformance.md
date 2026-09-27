# Conformance fixtures

The repository-level `conformance/` directory contains Draft 0.1 cases. Each
case has an `alo.yaml`, a pinned `graph.json`, and one or more run directories
under `runs/`. A run directory contains `input.json`, provider
`responses.json`, and `expected_run_record.json`.

To add a case, keep the ALO small and focused, add its input/response pairs,
compile it with `packages.compiler.graph_to_json`, and commit the resulting
Graph IR and Run Record fixtures. Add a test run that covers each behavior the
case is intended to pin. Golden Run Record checks ignore only `run_id` and
`timestamp`, because those values are inherently non-deterministic per run.
