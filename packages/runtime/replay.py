"""Replay completed ALO runs from their stored Run Record data."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from typing import Any

from packages.compiler import compile_alo
from packages.core import ensure_valid

from .engine import (
    ExecutionError,
    _build_decision_requests,
    _evaluate_derived_values,
    _evaluate_rules,
    _now,
)
from . import ENGINE_VERSION

__all__ = ["ReplayMismatch", "replay"]


class ReplayMismatch(ValueError):
    """Raised when replay does not reproduce the recorded result."""


def replay(document: Mapping[str, Any], run_record: Mapping[str, Any]) -> dict[str, Any]:
    """Re-execute rules using the input and decision results in ``run_record``.

    Replay never calls a Decision Provider. The stored normalized input and
    decision results are the complete decision context for the new evaluation.
    """

    ensure_valid(document)
    graph = compile_alo(document)
    alo = document["alo"]

    if not isinstance(run_record, Mapping):
        raise ReplayMismatch("run record must be an object")
    normalized_input = run_record.get("normalized_input")
    decision_results = run_record.get("decision_results")
    if not isinstance(normalized_input, Mapping):
        raise ReplayMismatch("normalized_input is missing or is not an object")
    if not isinstance(decision_results, Mapping):
        raise ReplayMismatch("decision_results is missing or is not an object")

    record: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "timestamp": _now(),
        "alo_id": alo["id"],
        "alo_version": alo["version"],
        "engine_version": ENGINE_VERSION,
        "graph_ir_version": graph["graph_ir_version"],
        "provider": run_record.get("provider"),
        "provider_model": run_record.get("provider_model"),
        "provider_config": copy.deepcopy(run_record.get("provider_config")),
        "threshold_version": alo.get("threshold_version"),
        "normalized_input": copy.deepcopy(dict(normalized_input)),
        "state_before": None,
        "decision_requests": [],
        "decision_results": copy.deepcopy(dict(decision_results)),
        "rule_trace": [],
        "state_after": None,
        "output": None,
        "status": "ok",
    }

    state_schema = alo.get("state_schema", {})
    state = {name: copy.deepcopy(field["initial"]) for name, field in state_schema.items()}
    record["state_before"] = copy.deepcopy(state)

    try:
        derived = _evaluate_derived_values(
            alo.get("derived_values", {}), record["normalized_input"], state
        )
        context: dict[str, Any] = {
            "input": record["normalized_input"],
            "state": state,
            "derived": derived,
            "threshold": dict(alo.get("thresholds", {})),
            "decision": record["decision_results"],
        }
        record["decision_requests"] = _build_decision_requests(graph, context)
        state_after, output, rule_trace, stop_condition = _evaluate_rules(
            graph, context
        )
    except (ExecutionError, ValueError) as error:
        record["status"] = "error"
        record["error"] = str(error)
        state_after, output, rule_trace, stop_condition = None, None, [], None

    if state_after is not None:
        record["state_after"] = state_after
        record["output"] = output
        record["rule_trace"] = rule_trace
        if stop_condition:
            record["status"] = stop_condition

    differences = [
        f"{field}: recorded={run_record.get(field)!r}, recomputed={record[field]!r}"
        for field in ("state_after", "output", "status")
        if run_record.get(field) != record[field]
    ]
    if differences:
        raise ReplayMismatch("replay mismatch: " + "; ".join(differences))
    return record
