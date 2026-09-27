"""Compile a canonical Draft 0.2 ALO document into an Object Graph IR.

Per docs/complete-implementation-guide.md section 6 ("ALO Diagram"), the
diagram must represent the object model (mainObj/subObjList/State/managerObj/
Input/Output and their relationships), not only execution/decision nodes.
This module is the object-model analogue of ``packages.compiler.compiler``
(which compiles the superseded Draft 0.1 workflow DSL); it is deliberately
separate rather than extending that module, since the two represent
different things (an object model vs. a decision workflow).

Minimum node types: MAIN_OBJECT, SUB_OBJECT, STATE, MANAGER, INPUT, OUTPUT.
Minimum relationships: CONTAINS, COORDINATES, READS_STATE, UPDATES_STATE,
RECEIVES, EMITS. Optional execution-overlay nodes (JEV_NOUL/JEV_CHOICE/
JEV_SCORE) are attached for any managerObj.process step that declares a
Jev calculation; they do not replace the conceptual graph.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

OBJECT_GRAPH_IR_VERSION = "0.2"

_JEV_NODE_TYPE = {"Noul": "JEV_NOUL", "Choice": "JEV_CHOICE", "Score": "JEV_SCORE"}


class ObjectGraphError(ValueError):
    """Raised when a document cannot be compiled into the Object Graph IR."""


def compile_object_graph(document: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a canonical (spec_version 0.2) ALO document into Object Graph IR."""

    if not isinstance(document, Mapping):
        raise ObjectGraphError("document must be an object")
    alo = document.get("alo")
    if not isinstance(alo, Mapping):
        raise ObjectGraphError("document must contain an 'alo' object")
    if alo.get("spec_version") != "0.2":
        raise ObjectGraphError(
            "compile_object_graph only supports canonical spec_version '0.2'"
        )

    main_obj = _mapping(alo.get("mainObj"), "alo.mainObj")
    sub_obj_list = _sequence(alo.get("subObjList"), "alo.subObjList")
    state = _mapping(alo.get("State"), "alo.State")
    manager_obj = _mapping(alo.get("managerObj"), "alo.managerObj")

    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()

    input_id = "input"
    output_id = "output"
    state_id = "state"
    main_id = f"main.{_require_id(main_obj, 'alo.mainObj')}"
    manager_id = f"manager.{manager_obj.get('id', 'manager')}"

    _add_node(
        nodes,
        input_id,
        "INPUT",
        {"fields": list(_sequence(manager_obj.get("input", []), "alo.managerObj.input"))},
    )
    _add_node(nodes, output_id, "OUTPUT", {"fields": list(
        _sequence(manager_obj.get("output", []), "alo.managerObj.output")
    )})
    _add_node(nodes, state_id, "STATE", {"fields": dict(state)})
    _add_node(
        nodes,
        main_id,
        "MAIN_OBJECT",
        {
            "id": main_obj.get("id"),
            "name": main_obj.get("name"),
            "purpose": main_obj.get("purpose"),
            "responsibilities": list(main_obj.get("responsibilities", [])),
        },
    )
    _add_node(
        nodes,
        manager_id,
        "MANAGER",
        {"id": manager_obj.get("id"), "process": _process_summary(manager_obj)},
    )

    sub_ids: list[str] = []
    for index, raw_sub in enumerate(sub_obj_list):
        sub_obj = _mapping(raw_sub, f"alo.subObjList[{index}]")
        sub_id = f"sub.{_require_id(sub_obj, f'alo.subObjList[{index}]')}"
        _add_node(
            nodes,
            sub_id,
            "SUB_OBJECT",
            {
                "id": sub_obj.get("id"),
                "name": sub_obj.get("name"),
                "purpose": sub_obj.get("purpose"),
                "responsibilities": list(sub_obj.get("responsibilities", [])),
            },
        )
        sub_ids.append(sub_id)

    edges.add((input_id, manager_id, "RECEIVES"))
    edges.add((manager_id, main_id, "COORDINATES"))
    edges.add((state_id, manager_id, "READS_STATE"))
    edges.add((manager_id, state_id, "UPDATES_STATE"))
    edges.add((manager_id, output_id, "EMITS"))
    for sub_id in sub_ids:
        edges.add((main_id, sub_id, "CONTAINS"))
        edges.add((manager_id, sub_id, "COORDINATES"))

    process = _sequence(manager_obj.get("process", []), "alo.managerObj.process")
    for index, raw_step in enumerate(process):
        step = _mapping(raw_step, f"alo.managerObj.process[{index}]")
        calculation = step.get("calculation")
        if not isinstance(calculation, Mapping):
            continue
        jev = calculation.get("jev")
        if not isinstance(jev, Mapping):
            continue
        jev_type = jev.get("type")
        node_type = _JEV_NODE_TYPE.get(jev_type)
        if node_type is None:
            raise ObjectGraphError(
                f"alo.managerObj.process[{index}].calculation.jev.type must be "
                f"one of {sorted(_JEV_NODE_TYPE)}: {jev_type!r}"
            )
        step_id = step.get("id", f"step_{index}")
        calc_id = f"calc.{step_id}"
        _add_node(
            nodes,
            calc_id,
            node_type,
            {"step_id": step_id, "question": jev.get("question")},
        )
        edges.add((manager_id, calc_id, "CALCULATES"))

    ordered_nodes = sorted(nodes.values(), key=lambda node: node["id"])
    ordered_edges = [
        {"id": f"{edge_type.lower()}:{source}->{target}", "from": source, "to": target, "type": edge_type}
        for source, target, edge_type in sorted(edges)
    ]

    return {
        "object_graph_ir_version": OBJECT_GRAPH_IR_VERSION,
        "source": {
            "spec_version": alo["spec_version"],
            "alo_id": alo.get("id"),
            "alo_version": alo.get("version"),
        },
        "nodes": ordered_nodes,
        "edges": ordered_edges,
    }


def _process_summary(manager_obj: Mapping[str, Any]) -> list[dict[str, Any]]:
    process = manager_obj.get("process", [])
    if not isinstance(process, Sequence) or isinstance(process, (str, bytes, bytearray)):
        return []
    summary = []
    for step in process:
        if not isinstance(step, Mapping):
            continue
        summary.append({"id": step.get("id"), "action": step.get("action")})
    return summary


def _add_node(
    nodes: dict[str, dict[str, Any]], node_id: str, node_type: str, data: dict[str, Any]
) -> None:
    if node_id in nodes:
        raise ObjectGraphError(f"duplicate Object Graph IR node id: {node_id}")
    nodes[node_id] = {"id": node_id, "type": node_type, "data": data}


def _require_id(obj: Mapping[str, Any], path: str) -> str:
    value = obj.get("id")
    if not isinstance(value, str) or not value:
        raise ObjectGraphError(f"{path}.id must be a non-empty string")
    return value


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ObjectGraphError(f"{path} must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ObjectGraphError(f"{path} must be an array")
    return value
