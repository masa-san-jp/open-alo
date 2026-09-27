"""Compile a loaded ALO document into canonical Graph IR.

The compiler deliberately accepts a mapping rather than a YAML path. Parsing
and schema validation are separate responsibilities and will be provided by
the validator/CLI layers.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


GRAPH_IR_VERSION = "0.1"

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_CONDITION_REFERENCE = re.compile(
    r"\b(?:input|state|derived|decision)"
    r"\.[A-Za-z][A-Za-z0-9_-]*"
    r"(?:\.[A-Za-z][A-Za-z0-9_-]*)*\b"
)

_NODE_ORDER = {
    "INPUT": 10,
    "STATE": 20,
    "DERIVE": 30,
    "DECISION_BINARY": 40,
    "DECISION_CATEGORICAL": 41,
    "DECISION_SCALAR": 42,
    "RULE": 50,
    "ACTION": 60,
    "OUTPUT": 70,
    "STOP": 80,
}


class CompileError(ValueError):
    """Raised when an ALO cannot be represented by the Draft 0.1 Graph IR."""


def compile_alo(document: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a loaded ALO mapping into a deterministic Graph IR mapping.

    The function performs the reference and target checks needed to construct
    a usable graph. It does not replace JSON Schema validation; callers should
    validate the source document before compiling it.
    """

    if not isinstance(document, Mapping):
        raise CompileError("ALO document must be an object")

    alo = document.get("alo")
    if not isinstance(alo, Mapping):
        raise CompileError("ALO document must contain an 'alo' object")

    for field in (
        "spec_version",
        "id",
        "version",
        "inputs",
        "state_schema",
        "decisions",
        "transition_rules",
        "outputs",
    ):
        if field not in alo:
            raise CompileError(f"missing required field: alo.{field}")

    if alo["spec_version"] != "0.1":
        raise CompileError("only ALO spec_version '0.1' is supported")

    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()

    inputs = _mapping(alo["inputs"], "alo.inputs")
    state_schema = _mapping(alo["state_schema"], "alo.state_schema")
    outputs = _mapping(alo["outputs"], "alo.outputs")
    derived_values = _mapping(alo.get("derived_values", {}), "alo.derived_values")
    decisions = _sequence(alo["decisions"], "alo.decisions")
    transition_rules = _sequence(
        alo["transition_rules"], "alo.transition_rules"
    )

    for name, schema in _sorted_items(inputs, "input"):
        _add_node(
            nodes,
            f"input.{name}",
            "INPUT",
            {"name": name, "schema": copy.deepcopy(schema)},
        )

    for name, schema in _sorted_items(state_schema, "state"):
        _add_node(
            nodes,
            f"state.{name}",
            "STATE",
            {"name": name, "schema": copy.deepcopy(schema)},
        )

    for name, definition in _sorted_items(derived_values, "derived value"):
        definition = _mapping(definition, f"alo.derived_values.{name}")
        expression = _required_string(
            definition, "expression", f"alo.derived_values.{name}"
        )
        data: dict[str, Any] = {
            "name": name,
            "expression": expression,
        }
        if "type" in definition:
            data["type"] = definition["type"]
        if "description" in definition:
            data["description"] = definition["description"]
        _add_node(nodes, f"derived.{name}", "DERIVE", data)

    decision_nodes: list[tuple[Mapping[str, Any], str]] = []
    for raw_decision in decisions:
        decision = _mapping(raw_decision, "alo.decisions[]")
        decision_id = _required_identifier(decision, "id", "decision")
        node_id = f"decision.{decision_id}"
        decision_type = _required_string(decision, "type", node_id)
        if decision_type not in {"binary", "categorical", "scalar"}:
            raise CompileError(
                f"{node_id}.type must be binary, categorical, or scalar"
            )
        reads = _string_sequence(decision.get("reads"), f"{node_id}.reads")
        question = _required_string(decision, "question", node_id)
        data: dict[str, Any] = {
            "name": decision_id,
            "decision_type": decision_type,
            "reads": list(reads),
            "question": question,
        }
        for optional in ("description", "options", "scale"):
            if optional in decision:
                data[optional] = copy.deepcopy(decision[optional])
        _add_node(
            nodes,
            node_id,
            f"DECISION_{decision_type.upper()}",
            data,
        )
        decision_nodes.append((decision, node_id))

    rule_nodes: list[tuple[Mapping[str, Any], str]] = []
    priorities: dict[int, str] = {}
    for raw_rule in transition_rules:
        rule = _mapping(raw_rule, "alo.transition_rules[]")
        rule_id = _required_identifier(rule, "id", "rule")
        node_id = f"rule.{rule_id}"
        priority = rule.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise CompileError(f"{node_id}.priority must be an integer")
        if priority in priorities:
            raise CompileError(
                "transition rule priorities must be unique: "
                f"{priorities[priority]} and {rule_id} both use {priority}"
            )
        priorities[priority] = rule_id
        when = _required_string(rule, "when", node_id)
        assignments = _mapping(rule.get("set"), f"{node_id}.set")
        data: dict[str, Any] = {
            "name": rule_id,
            "priority": priority,
            "when": when,
            "set": copy.deepcopy(dict(assignments)),
        }
        if "description" in rule:
            data["description"] = rule["description"]
        _add_node(nodes, node_id, "RULE", data)
        rule_nodes.append((rule, node_id))

    for name, schema in _sorted_items(outputs, "output"):
        _add_node(
            nodes,
            f"output.{name}",
            "OUTPUT",
            {"name": name, "schema": copy.deepcopy(schema)},
        )

    stop_conditions = _string_sequence(
        alo.get("stop_conditions", []), "alo.stop_conditions"
    )
    for index, condition in enumerate(stop_conditions, start=1):
        stop_id = f"stop.{_slug(condition, index)}"
        while stop_id in nodes:
            stop_id = f"{stop_id}-{index}"
        _add_node(
            nodes,
            stop_id,
            "STOP",
            {"condition": condition},
        )

    for decision, node_id in decision_nodes:
        for reference in _string_sequence(
            decision.get("reads"), f"{node_id}.reads"
        ):
            _add_reference_edge(nodes, edges, reference, node_id, "READS")

    for rule, node_id in rule_nodes:
        for reference in _condition_references(rule["when"]):
            _add_reference_edge(nodes, edges, reference, node_id, "GATES")
        assignments = _mapping(rule["set"], f"{node_id}.set")
        for target in assignments:
            _validate_identifier(target, f"{node_id}.set key")
            state_target = f"state.{target}"
            output_target = f"output.{target}"
            if state_target in nodes and output_target in nodes:
                raise CompileError(
                    f"{node_id}.set.{target} is ambiguous: it is both state and output"
                )
            if state_target in nodes:
                _add_edge(edges, node_id, state_target, "UPDATES")
            elif output_target in nodes:
                _add_edge(edges, node_id, output_target, "EMITS")
            else:
                raise CompileError(
                    f"{node_id}.set.{target} does not name a state or output field"
                )

    ordered_nodes = sorted(
        nodes.values(),
        key=lambda node: (_NODE_ORDER.get(node["type"], 999), node["id"]),
    )
    ordered_edges = [
        {
            "id": _edge_id(source, target, edge_type),
            "from": source,
            "to": target,
            "type": edge_type,
        }
        for source, target, edge_type in sorted(edges)
    ]

    return {
        "graph_ir_version": GRAPH_IR_VERSION,
        "source": {
            "spec_version": alo["spec_version"],
            "alo_id": alo["id"],
            "alo_version": alo["version"],
        },
        "nodes": ordered_nodes,
        "edges": ordered_edges,
    }


def graph_to_json(graph: Mapping[str, Any]) -> str:
    """Serialize Graph IR in a stable, human-readable JSON form."""

    return json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _add_node(
    nodes: dict[str, dict[str, Any]],
    node_id: str,
    node_type: str,
    data: dict[str, Any],
) -> None:
    if node_id in nodes:
        raise CompileError(f"duplicate Graph IR node id: {node_id}")
    nodes[node_id] = {"id": node_id, "type": node_type, "data": data}


def _add_edge(
    edges: set[tuple[str, str, str]], source: str, target: str, edge_type: str
) -> None:
    edges.add((source, target, edge_type))


def _add_reference_edge(
    nodes: Mapping[str, Any],
    edges: set[tuple[str, str, str]],
    reference: str,
    target: str,
    edge_type: str,
) -> None:
    source = _reference_node_id(reference)
    if source not in nodes:
        raise CompileError(f"unknown reference: {reference}")
    _add_edge(edges, source, target, edge_type)


def _reference_node_id(reference: str) -> str:
    parts = reference.split(".")
    if len(parts) < 2:
        raise CompileError(f"reference must include a name: {reference}")
    return ".".join(parts[:2])


def _condition_references(condition: str) -> list[str]:
    return sorted(set(_CONDITION_REFERENCE.findall(condition)))


def _edge_id(source: str, target: str, edge_type: str) -> str:
    return f"{edge_type.lower()}:{source}->{target}"


def _slug(value: str, index: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return slug or f"condition_{index}"


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CompileError(f"{path} must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CompileError(f"{path} must be an array")
    return value


def _string_sequence(value: Any, path: str | None) -> Sequence[str]:
    if value is None:
        raise CompileError(f"{path or 'value'} must be an array")
    values = _sequence(value, path or "value")
    for index, item in enumerate(values):
        if not isinstance(item, str) or not item:
            raise CompileError(f"{path or 'value'}[{index}] must be a non-empty string")
    return values  # type: ignore[return-value]


def _sorted_items(
    value: Mapping[str, Any], kind: str
) -> list[tuple[str, Any]]:
    for name in value:
        _validate_identifier(name, f"{kind} name")
    return sorted(value.items(), key=lambda item: item[0])


def _required_string(value: Mapping[str, Any], key: str, path: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise CompileError(f"{path}.{key} must be a non-empty string")
    return result


def _required_identifier(value: Mapping[str, Any], key: str, path: str) -> str:
    result = _required_string(value, key, path)
    _validate_identifier(result, f"{path}.{key}")
    return result


def _validate_identifier(value: str, path: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise CompileError(
            f"{path} must match ^[A-Za-z][A-Za-z0-9_-]*$: {value!r}"
        )
