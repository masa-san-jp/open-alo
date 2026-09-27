# Object Graph IR

Object Graph IR is the canonical intermediate representation between a
canonical ALO source document (`mainObj`/`subObjList`/`State`/`managerObj`
-- see `docs/spec.md`) and generated views (Mermaid, SVG). It represents the
ALO's **object structure**, not a decision workflow: a decision-only graph
does not satisfy this representation (see
`docs/complete-implementation-guide.md` section 6, and
`docs/implementation-correction.md` for why the earlier Draft 0.1 workflow
Graph IR was superseded).

## Envelope

```json
{
  "object_graph_ir_version": "0.2",
  "source": {
    "spec_version": "0.2",
    "alo_id": "learning-coach",
    "alo_version": "0.1.0"
  },
  "nodes": [],
  "edges": []
}
```

`object_graph_ir_version` versions the IR independently from the ALO source
schema. The source block preserves the ALO identity needed for caching,
comparison, and reproducibility.

## Nodes

Every node has this shape:

```json
{
  "id": "main.learning_coach",
  "type": "MAIN_OBJECT",
  "data": {}
}
```

The minimum required node types (`docs/complete-implementation-guide.md`
section 6):

| ALO element | Node ID | Node type |
| --- | --- | --- |
| `managerObj.input` | `input` | `INPUT` |
| `mainObj` | `main.<mainObj id>` | `MAIN_OBJECT` |
| each `subObjList` entry | `sub.<subObj id>` | `SUB_OBJECT` |
| `State` (one aggregate node) | `state` | `STATE` |
| `managerObj` | `manager.<managerObj id>` | `MANAGER` |
| `managerObj.output` | `output` | `OUTPUT` |

Optional execution-overlay nodes, one per `managerObj.process` step that
declares a Jev calculation:

| Jev calculation type | Node type |
| --- | --- |
| `Noul` | `JEV_NOUL` |
| `Choice` | `JEV_CHOICE` |
| `Score` | `JEV_SCORE` |

These overlay nodes document what the step *would* calculate; they do not
replace the conceptual graph, and a graph with none of them (no Jev
calculations declared) is still a complete, conformant Object Graph IR.

## Edges

Every edge has this shape:

```json
{
  "id": "receives:input->manager.learning_coach_manager",
  "from": "input",
  "to": "manager.learning_coach_manager",
  "type": "RECEIVES"
}
```

The minimum required relationships:

| Edge type | Meaning |
| --- | --- |
| `RECEIVES` | Input reaches the manager |
| `COORDINATES` | The manager coordinates `mainObj` and each `subObjList` entry |
| `CONTAINS` | `mainObj` composes a `subObjList` entry |
| `READS_STATE` | The manager reads `State` |
| `UPDATES_STATE` | The manager updates `State` |
| `EMITS` | The manager produces `Output` |

Plus one optional relationship for the execution overlay:

| Edge type | Meaning |
| --- | --- |
| `CALCULATES` | The manager invokes a Jev calculation node for one process step |

The compiler sorts nodes and edges deterministically. Edge IDs are derived
from their source, target, and type, so the same ALO produces the same
serialized Object Graph IR regardless of mapping insertion order.

## Compiler API

```python
from packages.compiler import compile_object_graph, graph_to_json

graph = compile_object_graph(parsed_document)
print(graph_to_json(graph))
```

`compile_object_graph` requires a canonical (`spec_version: "0.2"`) document
and raises `ObjectGraphError` if `mainObj`, `subObjList`, `State`, or
`managerObj` is missing, or if a process step declares an unknown Jev
calculation type.

## Diagram output

```python
from packages.compiler import render_mermaid, render_svg

mermaid = render_mermaid(graph)
svg = render_svg(graph)
```

Both renderers operate generically on any `{nodes, edges}` Graph IR (they
are shared with `packages.compiler.compile_object_graph`'s output; there is
no Object-Graph-IR-specific renderer). Node shapes and colors distinguish
`MAIN_OBJECT`, `SUB_OBJECT`, `STATE`, `MANAGER`, `INPUT`/`OUTPUT`, and the
`JEV_*` overlay nodes. Labels are escaped and IDs are sanitized with
deterministic collision handling. `render_mermaid` accepts `TB`, `TD`, `BT`,
`RL`, or `LR` as the optional direction.
