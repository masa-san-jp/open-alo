# Graph IR — Draft 0.1

Graph IR is the canonical intermediate representation between an ALO source
document and generated views or runtime execution. Mermaid is a view of Graph
IR; it is not a second source format.

## Envelope

```json
{
  "graph_ir_version": "0.1",
  "source": {
    "spec_version": "0.1",
    "alo_id": "support-triage",
    "alo_version": "0.1.0"
  },
  "nodes": [],
  "edges": []
}
```

`graph_ir_version` versions the IR independently from the ALO source schema.
The source block preserves the ALO identity needed for caching, comparison,
and reproducibility.

## Nodes

Every node has this shape:

```json
{
  "id": "decision.category",
  "type": "DECISION_CATEGORICAL",
  "data": {}
}
```

Node IDs are stable names formed from a namespace and identifier:

| ALO element | Node ID | Node type |
| --- | --- | --- |
| input `message` | `input.message` | `INPUT` |
| state `status` | `state.status` | `STATE` |
| derived value `priority` | `derived.priority` | `DERIVE` |
| binary decision `is_emergency` | `decision.is_emergency` | `DECISION_BINARY` |
| categorical decision `category` | `decision.category` | `DECISION_CATEGORICAL` |
| scalar decision `confidence` | `decision.confidence` | `DECISION_SCALAR` |
| transition rule `route` | `rule.route` | `RULE` |
| output `action` | `output.action` | `OUTPUT` |
| stop condition | `stop.<condition>` | `STOP` |

`ACTION` is reserved for a future explicit action declaration. Draft 0.1
represents rule assignments directly with `UPDATES` and `EMITS` edges.

## Edges

Every edge has this shape:

```json
{
  "id": "reads:input.message->decision.category",
  "from": "input.message",
  "to": "decision.category",
  "type": "READS"
}
```

The initial edge types are:

| Edge type | Meaning in Draft 0.1 |
| --- | --- |
| `READS` | A decision reads an input, state, or derived value |
| `GATES` | A rule condition refers to a decision, input, state, or derived value |
| `UPDATES` | A rule writes a state field |
| `EMITS` | A rule writes an output field |
| `DEPENDS_ON` | Reserved for compiler dependencies not represented by the minimal compiler |
| `STOPS` | A rule declares that matching it ends the run with a named stop condition |

When a `set` target is declared both as a state field and as an output field,
the compiler emits both an `UPDATES` edge and an `EMITS` edge. This supports
the common pattern where a rule updates state and exposes the same value as an
output.

A transition rule may declare an optional `stop_condition`, whose value must
be one of the ALO's declared `stop_conditions`. The compiler emits a `STOPS`
edge from the rule to the matching `STOP` node, and the reference runtime
reports that stop condition as the Run Record's `status` when the rule
matches.

The compiler sorts nodes and edges deterministically. Edge IDs are derived from
their source, target, and type, so the same ALO produces the same serialized
Graph IR regardless of mapping insertion order.

## Compiler API

The current reference compiler accepts a parsed mapping. YAML parsing and JSON
Schema validation are separate layers and are not hidden inside the compiler.

```python
from packages.compiler import compile_alo, graph_to_json

graph = compile_alo(parsed_document)
print(graph_to_json(graph))
```

The compiler rejects unresolved references, unknown rule targets, duplicate
node IDs, and duplicate transition priorities. It does not interpret the
expression language for derived values; that language is intentionally not
frozen in ALO Draft 0.1.

## Mermaid output

The reference renderer converts Graph IR into a `flowchart TD` diagram by
default:

```python
from packages.compiler import render_mermaid

mermaid = render_mermaid(graph)
```

Node shapes distinguish inputs, state, decisions, rules, outputs, and stop
conditions. Edge labels preserve the Graph IR edge type. Labels are HTML-
escaped and Mermaid IDs are sanitized with deterministic collision handling.
The renderer accepts `TB`, `TD`, `BT`, `RL`, or `LR` as the optional direction.
