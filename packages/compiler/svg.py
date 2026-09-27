"""Render canonical Open ALO Graph IR as a self-contained SVG diagram."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from typing import Any


class SvgError(ValueError):
    """Raised when Graph IR cannot be rendered as an SVG diagram."""


_DIRECTIONS = {"TB", "TD", "BT", "RL", "LR"}
_TYPE_ORDER = {
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
_PALETTE = {
    "INPUT": ("#e3f2fd", "#1565c0", "#0d47a1"),
    "STATE": ("#f3e5f5", "#6a1b9a", "#4a148c"),
    "DERIVE": ("#fff3e0", "#ef6c00", "#e65100"),
    "DECISION_BINARY": ("#fffde7", "#f9a825", "#5f4300"),
    "DECISION_CATEGORICAL": ("#fffde7", "#f9a825", "#5f4300"),
    "DECISION_SCALAR": ("#fffde7", "#f9a825", "#5f4300"),
    "RULE": ("#e8f5e9", "#2e7d32", "#1b5e20"),
    "ACTION": ("#fce4ec", "#ad1457", "#880e4f"),
    "OUTPUT": ("#ede7f6", "#4527a0", "#311b92"),
    "STOP": ("#ffebee", "#c62828", "#b71c1c"),
}
_MARGIN = 28
_BOX_WIDTH = 220
_BOX_HEIGHT = 72
_COLUMN_GAP = 32
_ROW_GAP = 42
_MAX_LABEL_LINES = 3
_MAX_LINE_LENGTH = 30


def render_svg(graph: Mapping[str, Any], direction: str = "TD") -> str:
    """Render Graph IR as deterministic, dependency-free SVG.

    Nodes are arranged in type-ordered rows (or columns for horizontal
    directions). Node and edge input order does not affect the output.
    """

    if direction not in _DIRECTIONS:
        allowed = ", ".join(sorted(_DIRECTIONS))
        raise SvgError(f"direction must be one of {allowed}: {direction!r}")

    nodes = _validate_nodes(graph.get("nodes"))
    edges = _validate_edges(graph.get("edges"), nodes)
    ordered_nodes = sorted(
        nodes,
        key=lambda node: (_TYPE_ORDER.get(node["type"], 999), node["type"], node["id"]),
    )
    rows: list[list[dict[str, Any]]] = []
    for node in ordered_nodes:
        node_rank = (_TYPE_ORDER.get(node["type"], 999), node["type"])
        if not rows or (
            (_TYPE_ORDER.get(rows[-1][0]["type"], 999), rows[-1][0]["type"])
            != node_rank
        ):
            rows.append([])
        rows[-1].append(node)

    is_vertical = direction in {"TD", "TB", "BT"}
    max_items = max((len(row) for row in rows), default=1)
    if is_vertical:
        width = 2 * _MARGIN + max_items * _BOX_WIDTH + (max_items - 1) * _COLUMN_GAP
        height = 2 * _MARGIN + len(rows) * _BOX_HEIGHT + (len(rows) - 1) * _ROW_GAP
    else:
        width = 2 * _MARGIN + len(rows) * _BOX_WIDTH + (len(rows) - 1) * _ROW_GAP
        height = 2 * _MARGIN + max_items * _BOX_HEIGHT + (max_items - 1) * _COLUMN_GAP

    positions: dict[str, tuple[float, float]] = {}
    row_sequence = list(reversed(rows)) if direction in {"BT", "RL"} else rows
    for row_index, row in enumerate(row_sequence):
        for item_index, node in enumerate(row):
            if is_vertical:
                x = _MARGIN + item_index * (_BOX_WIDTH + _COLUMN_GAP)
                y = _MARGIN + row_index * (_BOX_HEIGHT + _ROW_GAP)
            else:
                x = _MARGIN + row_index * (_BOX_WIDTH + _ROW_GAP)
                y = _MARGIN + item_index * (_BOX_HEIGHT + _COLUMN_GAP)
            positions[node["id"]] = (x, y)

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="title description">',
        "  <title id=\"title\">Open ALO workflow graph</title>",
        "  <desc id=\"description\">Deterministic Graph IR visualization</desc>",
        "  <defs>",
        '    <marker id="arrowhead" markerWidth="8" markerHeight="7" '
        'refX="7" refY="3.5" orient="auto" markerUnits="strokeWidth">',
        '      <path d="M0,0 L8,3.5 L0,7 z" fill="#546e7a"/>',
        "    </marker>",
        "  </defs>",
        '  <g class="edges" fill="none" stroke="#546e7a" stroke-width="1.5">',
    ]
    for edge in edges:
        path, label_x, label_y = _edge_geometry(edge, positions, is_vertical)
        lines.append(
            f'    <path d="{path}" marker-end="url(#arrowhead)"/>'
        )
        lines.append(
            f'    <text x="{label_x:g}" y="{label_y:g}" fill="#455a64" '
            f'class="edge-label">{_escape_text(edge["type"])}</text>'
        )
    lines.append("  </g>")

    lines.append('  <g class="nodes" font-family="sans-serif">')
    for node in ordered_nodes:
        x, y = positions[node["id"]]
        fill, stroke, text_color = _PALETTE.get(
            node["type"], ("#eceff1", "#607d8b", "#263238")
        )
        radius = 16 if node["type"] == "STOP" else 10
        lines.append(
            f'    <g class="node" data-node-id="{_escape_attribute(node["id"])}">'
        )
        lines.append(
            f'      <rect x="{x:g}" y="{y:g}" width="{_BOX_WIDTH}" '
            f'height="{_BOX_HEIGHT}" rx="{radius}" ry="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        labels = _label_lines(node)
        text_x = x + _BOX_WIDTH / 2
        first_y = y + 24 - (len(labels) - 1) * 7
        for line_index, label in enumerate(labels):
            weight = "bold" if line_index == 0 else "normal"
            lines.append(
                f'      <text x="{text_x:g}" y="{first_y + line_index * 16:g}" '
                f'text-anchor="middle" fill="{text_color}" font-size="12" '
                f'font-weight="{weight}">{_escape_text(label)}</text>'
            )
        lines.append("    </g>")
    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def _edge_geometry(
    edge: Mapping[str, str],
    positions: Mapping[str, tuple[float, float]],
    is_vertical: bool,
) -> tuple[str, float, float]:
    source_x, source_y = positions[edge["from"]]
    target_x, target_y = positions[edge["to"]]
    source_center = (source_x + _BOX_WIDTH / 2, source_y + _BOX_HEIGHT / 2)
    target_center = (target_x + _BOX_WIDTH / 2, target_y + _BOX_HEIGHT / 2)
    if is_vertical:
        down = target_center[1] >= source_center[1]
        start_y = source_y + (_BOX_HEIGHT if down else 0)
        end_y = target_y + (0 if down else _BOX_HEIGHT)
        start = (source_center[0], start_y)
        end = (target_center[0], end_y)
        bend_y = (start[1] + end[1]) / 2
        path = f"M{start[0]:g},{start[1]:g} V{bend_y:g} H{end[0]:g} V{end[1]:g}"
        return path, (start[0] + end[0]) / 2, bend_y - 4
    right = target_center[0] >= source_center[0]
    start_x = source_x + (_BOX_WIDTH if right else 0)
    end_x = target_x + (0 if right else _BOX_WIDTH)
    start = (start_x, source_center[1])
    end = (end_x, target_center[1])
    bend_x = (start[0] + end[0]) / 2
    path = f"M{start[0]:g},{start[1]:g} H{bend_x:g} V{end[1]:g} H{end[0]:g}"
    return path, bend_x, (start[1] + end[1]) / 2 - 4


def _validate_nodes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SvgError("Graph IR nodes must be an array")
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_node in enumerate(value):
        if not isinstance(raw_node, Mapping):
            raise SvgError(f"nodes[{index}] must be an object")
        node_id = raw_node.get("id")
        node_type = raw_node.get("type")
        if not isinstance(node_id, str) or not node_id:
            raise SvgError(f"nodes[{index}].id must be a non-empty string")
        if node_id in seen:
            raise SvgError(f"duplicate Graph IR node id: {node_id}")
        if not isinstance(node_type, str) or not node_type:
            raise SvgError(f"nodes[{index}].type must be a non-empty string")
        seen.add(node_id)
        nodes.append(dict(raw_node))
    return nodes


def _validate_edges(value: Any, nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SvgError("Graph IR edges must be an array")
    node_ids = {node["id"] for node in nodes}
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw_edge in enumerate(value):
        if not isinstance(raw_edge, Mapping):
            raise SvgError(f"edges[{index}] must be an object")
        source = raw_edge.get("from")
        target = raw_edge.get("to")
        edge_type = raw_edge.get("type")
        if not all(isinstance(item, str) and item for item in (source, target, edge_type)):
            raise SvgError(f"edges[{index}] requires non-empty from, to, and type")
        if source not in node_ids or target not in node_ids:
            raise SvgError(
                f"edges[{index}] references an unknown node: {source} -> {target}"
            )
        key = (source, target, edge_type)
        if key in seen:
            raise SvgError(f"duplicate Graph IR edge: {source} -> {target} ({edge_type})")
        seen.add(key)
        edges.append({"from": source, "to": target, "type": edge_type})
    return sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["type"]))


def _label_lines(node: Mapping[str, Any]) -> list[str]:
    data = node.get("data")
    data = data if isinstance(data, Mapping) else {}
    value = data.get("name") or data.get("condition") or data.get("expression") or node["id"]
    text = re.sub(r"\s+", " ", str(value)).strip()
    words = text.split(" ") or [node["id"]]
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > _MAX_LINE_LENGTH:
            word = word[: _MAX_LINE_LENGTH - 1] + "…"
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > _MAX_LINE_LENGTH:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > _MAX_LABEL_LINES:
        lines = lines[:_MAX_LABEL_LINES]
        lines[-1] = lines[-1][: _MAX_LINE_LENGTH - 1] + "…"
    if not lines:
        lines = [node["id"]]
    return [str(node["type"])] + lines


def _escape_text(value: Any) -> str:
    return html.escape(re.sub(r"[\r\n]+", " ", str(value)), quote=True)


def _escape_attribute(value: Any) -> str:
    return html.escape(str(value), quote=True)
