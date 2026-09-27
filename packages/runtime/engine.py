"""Execute a compiled ALO Graph IR against a Decision Provider.

The engine follows the processing model from docs/spec.md section 2: inputs
are normalized, state(t) and derived values are established, decisions are
requested from the provider, transition rules are evaluated once in priority
order against that fixed snapshot, and state(t+1)/output are produced
together with a Run Record (docs/spec.md section 12).
"""

from __future__ import annotations

import copy
import datetime
import uuid
from collections.abc import Mapping
from typing import Any

from packages.compiler import compile_alo
from packages.core import ensure_valid

from .expressions import ExpressionError, evaluate

__all__ = ["ExecutionError", "run"]


class ExecutionError(ValueError):
    """Raised when an ALO document cannot be executed."""


_FIELD_TYPE_CHECKS: dict[str, Any] = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "object": lambda value: isinstance(value, Mapping),
    "array": lambda value: isinstance(value, list),
}


def run(
    document: Mapping[str, Any],
    input_data: Mapping[str, Any],
    provider: Any,
    *,
    run_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Execute one pass of an ALO document and return its Run Record."""

    ensure_valid(document)
    graph = compile_alo(document)
    alo = document["alo"]

    record: dict[str, Any] = {
        "run_id": run_id or str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "alo_id": alo["id"],
        "alo_version": alo["version"],
        "provider": getattr(provider, "name", provider.__class__.__name__),
        "provider_model": getattr(provider, "model", None),
        "provider_config": getattr(provider, "config", None),
        "threshold_version": None,
        "normalized_input": None,
        "state_before": None,
        "decision_requests": [],
        "decision_results": {},
        "rule_trace": [],
        "state_after": None,
        "output": None,
        "status": "ok",
    }

    input_schema = alo.get("inputs", {})
    try:
        normalized_input = _normalize_input(input_schema, input_data)
    except ExecutionError as error:
        record["status"] = "input_error"
        record["error"] = str(error)
        return record
    record["normalized_input"] = normalized_input

    state_schema = alo.get("state_schema", {})
    state = {name: copy.deepcopy(field["initial"]) for name, field in state_schema.items()}
    record["state_before"] = copy.deepcopy(state)

    thresholds = dict(alo.get("thresholds", {}))

    try:
        derived = _evaluate_derived_values(
            alo.get("derived_values", {}), normalized_input, state
        )
    except ExecutionError as error:
        record["status"] = "error"
        record["error"] = str(error)
        return record

    context: dict[str, Any] = {
        "input": normalized_input,
        "state": state,
        "derived": derived,
        "threshold": thresholds,
    }

    decision_results: dict[str, dict[str, float]] = {}
    try:
        for node in _nodes_by_type(
            graph, "DECISION_BINARY", "DECISION_CATEGORICAL", "DECISION_SCALAR"
        ):
            data = node["data"]
            decision_id = data["name"]
            reads = {
                reference: evaluate(reference, context) for reference in data["reads"]
            }
            record["decision_requests"].append(
                {"id": decision_id, "type": data["decision_type"], "reads": reads}
            )
            if data["decision_type"] == "binary":
                result = provider.binary(decision_id, reads, data["question"])
            elif data["decision_type"] == "categorical":
                options = sorted(data.get("options", {}))
                result = provider.categorical(decision_id, reads, data["question"], options)
            else:
                result = provider.scalar(decision_id, reads, data["question"], data["scale"])
            decision_results[decision_id] = dict(result)
    except ExpressionError as error:
        record["status"] = "error"
        record["error"] = str(error)
        return record

    record["decision_results"] = decision_results
    context["decision"] = decision_results

    state_after = copy.deepcopy(state)
    output: dict[str, Any] = {}
    matched_any = False
    triggered_stop_condition: str | None = None
    rule_targets = _rule_targets(graph)

    rule_nodes = sorted(
        _nodes_by_type(graph, "RULE"), key=lambda node: node["data"]["priority"]
    )
    for node in rule_nodes:
        data = node["data"]
        rule_context = dict(context)
        rule_context["no_previous_rule_matched"] = not matched_any
        try:
            matched = bool(evaluate(data["when"], rule_context))
        except ExpressionError as error:
            record["status"] = "error"
            record["error"] = f"rule.{data['name']}: {error}"
            return record

        trace_entry: dict[str, Any] = {
            "id": data["name"],
            "priority": data["priority"],
            "matched": matched,
        }
        if matched:
            matched_any = True
            state_targets, output_targets = rule_targets.get(
                node["id"], (frozenset(), frozenset())
            )
            assignments = {
                target: value
                for target, value in data["set"].items()
                if target in state_targets or target in output_targets
            }
            trace_entry["set"] = assignments
            for target, value in assignments.items():
                if target in state_targets:
                    state_after[target] = value
                if target in output_targets:
                    output[target] = value
            triggered_stop_condition = data.get("stop_condition")
        record["rule_trace"].append(trace_entry)
        if matched:
            # First-match-wins: rules are an if/elif/.../else chain ordered by
            # priority, and `no_previous_rule_matched` is the else branch.
            # Once a rule matches, lower-priority rules are not evaluated.
            break

    record["state_after"] = state_after
    record["output"] = output
    if triggered_stop_condition:
        record["status"] = triggered_stop_condition
    return record


def _normalize_input(
    input_schema: Mapping[str, Any], input_data: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(input_data, Mapping):
        raise ExecutionError("input must be an object")

    unknown = sorted(set(input_data) - set(input_schema))
    if unknown:
        raise ExecutionError(f"unknown input field(s): {', '.join(unknown)}")

    normalized: dict[str, Any] = {}
    for name, field in input_schema.items():
        if name in input_data:
            value = input_data[name]
            _check_field_type(value, field, f"input.{name}")
            normalized[name] = value
        elif field.get("required"):
            raise ExecutionError(f"missing required input: {name}")
        elif "default" in field:
            normalized[name] = copy.deepcopy(field["default"])
    return normalized


def _check_field_type(value: Any, field: Mapping[str, Any], path: str) -> None:
    field_type = field.get("type")
    if field_type == "enum":
        values = field.get("values", [])
        if value not in values:
            raise ExecutionError(f"{path} must be one of {values!r}: {value!r}")
        return
    checker = _FIELD_TYPE_CHECKS.get(field_type)
    if checker is not None and not checker(value):
        raise ExecutionError(f"{path} must be of type {field_type}: {value!r}")


def _evaluate_derived_values(
    derived_schema: Mapping[str, Any],
    input_data: Mapping[str, Any],
    state: Mapping[str, Any],
) -> dict[str, Any]:
    derived: dict[str, Any] = {}
    context = {"input": input_data, "state": state, "derived": derived}
    for name in sorted(derived_schema):
        expression = derived_schema[name]["expression"]
        try:
            derived[name] = evaluate(expression, context)
        except ExpressionError as error:
            raise ExecutionError(f"derived.{name}: {error}") from error
    return derived


def _nodes_by_type(graph: Mapping[str, Any], *types: str) -> list[dict[str, Any]]:
    return [node for node in graph["nodes"] if node["type"] in types]


def _rule_targets(
    graph: Mapping[str, Any],
) -> dict[str, tuple[frozenset[str], frozenset[str]]]:
    state_targets: dict[str, set[str]] = {}
    output_targets: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        if edge["type"] == "UPDATES":
            state_targets.setdefault(edge["from"], set()).add(edge["to"].split(".", 1)[1])
        elif edge["type"] == "EMITS":
            output_targets.setdefault(edge["from"], set()).add(edge["to"].split(".", 1)[1])
    sources = set(state_targets) | set(output_targets)
    return {
        source: (
            frozenset(state_targets.get(source, ())),
            frozenset(output_targets.get(source, ())),
        )
        for source in sources
    }


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
