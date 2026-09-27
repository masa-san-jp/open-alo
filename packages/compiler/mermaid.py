"""Render canonical Open ALO Graph IR as Mermaid flowcharts."""

from __future__ import annotations

import hashlib
import html
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


class MermaidError(ValueError):
    """Raised when Graph IR cannot be rendered as a Mermaid flowchart."""


_DIRECTIONS = {"TB", "TD", "BT", "RL", "LR"}
_NODE_CLASSES = {
    "INPUT": "input",
    "STATE": "state",
    "DERIVE": "derive",
    "DECISION_BINARY": "decision",
    "DECISION_CATEGORICAL": "decision",
    "DECISION_SCALAR": "decision",
    "RULE": "rule",
    "ACTION": "action",
    "OUTPUT": "output",
    "STOP": "stop",
    # Canonical Draft 0.2 object model (packages.compiler.objectgraph).
    "MAIN_OBJECT": "mainobj",
    "SUB_OBJECT": "subobj",
    "MANAGER": "manager",
    "JEV_NOUL": "jev",
    "JEV_CHOICE": "jev",
    "JEV_SCORE": "jev",
    "DETERMINISTIC_CALC": "calc",
    "EXTERNAL_TOOL": "tool",
}
_NODE_SHAPES = {
    "INPUT": ("([", "])"),
    "STATE": ("[/", "/]"),
    "DERIVE": ("[[", "]]"),
    "DECISION_BINARY": ("{", "}"),
    "DECISION_CATEGORICAL": ("{", "}"),
    "DECISION_SCALAR": ("{", "}"),
    "RULE": ("[", "]"),
    "ACTION": ("([", "])"),
    "OUTPUT": ("([", "])"),
    "STOP": ("((", "))"),
    # Canonical Draft 0.2 object model.
    "MAIN_OBJECT": ("[[", "]]"),
    "SUB_OBJECT": ("[", "]"),
    "MANAGER": ("{{", "}}"),
    "JEV_NOUL": ("{", "}"),
    "JEV_CHOICE": ("{", "}"),
    "JEV_SCORE": ("{", "}"),
    "DETERMINISTIC_CALC": ("[", "]"),
    "EXTERNAL_TOOL": (">", "]"),
}


def render_mermaid(graph: Mapping[str, Any], direction: str = "TD") -> str:
    """Render Graph IR to a deterministic Mermaid flowchart.

    Nodes and edges are sorted by their canonical identifiers before rendering,
    so equivalent Graph IR mappings produce identical output. Mermaid IDs are
    derived from Graph IR IDs and receive a short hash only when sanitization
    would make two IDs collide.
    """

    if direction not in _DIRECTIONS:
        allowed = ", ".join(sorted(_DIRECTIONS))
        raise MermaidError(f"direction must be one of {allowed}: {direction!r}")

    nodes = _validate_nodes(graph.get("nodes"))
    edges = _validate_edges(graph.get("edges"), nodes)
    mermaid_ids = _mermaid_ids(nodes)

    lines = [f"flowchart {direction}"]
    source = graph.get("source")
    if isinstance(source, Mapping):
        alo_id = _single_line(source.get("alo_id", ""))
        alo_version = _single_line(source.get("alo_version", ""))
        if alo_id or alo_version:
            lines.append(f"    %% Open ALO: {_escape_text(alo_id)}@{_escape_text(alo_version)}")

    for node in sorted(nodes, key=lambda item: item["id"]):
        node_id = node["id"]
        node_type = node["type"]
        data = node.get("data")
        data = data if isinstance(data, Mapping) else {}
        name = data.get("name") or data.get("condition") or node_id
        label = f"{_escape_text(name)}<br/>{_escape_text(node_type)}"
        left, right = _NODE_SHAPES.get(node_type, ("[", "]"))
        lines.append(
            f'    {mermaid_ids[node_id]}{left}"{label}"{right}'
        )

    for edge in edges:
        lines.append(
            f"    {mermaid_ids[edge['from']]} -->|{edge['type']}| "
            f"{mermaid_ids[edge['to']]}"
        )

    for node in sorted(nodes, key=lambda item: item["id"]):
        node_class = _NODE_CLASSES.get(node["type"])
        if node_class:
            lines.append(f"    class {mermaid_ids[node['id']]} {node_class}")

    lines.extend(
        [
            "",
            "    classDef input fill:#e3f2fd,stroke:#1565c0,color:#0d47a1",
            "    classDef state fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c",
            "    classDef derive fill:#fff3e0,stroke:#ef6c00,color:#e65100",
            "    classDef decision fill:#fffde7,stroke:#f9a825,color:#5f4300",
            "    classDef rule fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20",
            "    classDef action fill:#fce4ec,stroke:#ad1457,color:#880e4f",
            "    classDef output fill:#ede7f6,stroke:#4527a0,color:#311b92",
            "    classDef stop fill:#ffebee,stroke:#c62828,color:#b71c1c",
            "    classDef mainobj fill:#fff8e1,stroke:#f57f17,color:#e65100",
            "    classDef subobj fill:#e8eaf6,stroke:#3949ab,color:#1a237e",
            "    classDef manager fill:#fce4ec,stroke:#ad1457,color:#880e4f",
            "    classDef jev fill:#fffde7,stroke:#f9a825,color:#5f4300",
            "    classDef calc fill:#e0f2f1,stroke:#00695c,color:#004d40",
            "    classDef tool fill:#efebe9,stroke:#5d4037,color:#3e2723",
        ]
    )
    return "\n".join(lines) + "\n"


def _validate_nodes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise MermaidError("Graph IR nodes must be an array")
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_node in enumerate(value):
        if not isinstance(raw_node, Mapping):
            raise MermaidError(f"nodes[{index}] must be an object")
        node_id = raw_node.get("id")
        node_type = raw_node.get("type")
        if not isinstance(node_id, str) or not node_id:
            raise MermaidError(f"nodes[{index}].id must be a non-empty string")
        if node_id in seen:
            raise MermaidError(f"duplicate Graph IR node id: {node_id}")
        if not isinstance(node_type, str) or not node_type:
            raise MermaidError(f"nodes[{index}].type must be a non-empty string")
        seen.add(node_id)
        nodes.append(dict(raw_node))
    return nodes


def _validate_edges(value: Any, nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise MermaidError("Graph IR edges must be an array")
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw_edge in enumerate(value):
        if not isinstance(raw_edge, Mapping):
            raise MermaidError(f"edges[{index}] must be an object")
        source = raw_edge.get("from")
        target = raw_edge.get("to")
        edge_type = raw_edge.get("type")
        if not all(isinstance(item, str) and item for item in (source, target, edge_type)):
            raise MermaidError(f"edges[{index}] requires non-empty from, to, and type")
        if source not in node_ids or target not in node_ids:
            raise MermaidError(
                f"edges[{index}] references an unknown node: {source} -> {target}"
            )
        key = (source, target, edge_type)
        if key in seen:
            raise MermaidError(f"duplicate Graph IR edge: {source} -> {target} ({edge_type})")
        seen.add(key)
        edges.append({"from": source, "to": target, "type": edge_type})
    return sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["type"]))


def _mermaid_ids(nodes: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    candidates: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        node_id = node["id"]
        candidates[_safe_id(node_id)].append(node_id)

    result: dict[str, str] = {}
    for base, node_ids in candidates.items():
        if len(node_ids) == 1:
            result[node_ids[0]] = base
            continue
        for node_id in sorted(node_ids):
            digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()[:8]
            result[node_id] = f"{base}_{digest}"
    return result


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not safe or not safe[0].isalpha():
        safe = f"n_{safe}"
    return f"n_{safe}"


def _single_line(value: Any) -> str:
    return re.sub(r"[\r\n]+", " ", str(value)).strip()


def _escape_text(value: Any) -> str:
    return html.escape(_single_line(value), quote=True)
