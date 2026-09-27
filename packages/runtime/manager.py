"""Execute a canonical Draft 0.2 ALO's managerObj process.

Per docs/complete-implementation-guide.md sections 13, 23-24: the runtime
is an implementation of managerObj semantics, not the definition of ALO.
Not every manager behavior can become a mechanical calculation -- some
`process` steps are language-defined (interpreting intent, generating an
explanation, ...) and are not simulated here; this reference runtime
executes the *mechanical* parts (Jev/provider calculations, declared
`state_updates`) and records a reproducibility trace for the rest, honest
about which steps it actually computed versus merely observed.

Jev is optional (docs/spec.md section 20 invariant: "Jev is optional").
A process step's ``calculation.provider`` may be the literal string
``"optional"`` (matching examples/canonical-minimal/alo.yaml); when no
provider is configured, an optional calculation is skipped rather than
failing the run. A calculation without that marker requires a provider.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from .expressions import ExpressionError, evaluate

__all__ = ["ManagerError", "run_manager"]

_JEV_METHOD = {"Noul": "binary", "Choice": "categorical", "Score": "scalar"}


class ManagerError(ValueError):
    """Raised when a canonical ALO's managerObj cannot be executed."""


def run_manager(
    document: Mapping[str, Any],
    input_data: Mapping[str, Any],
    provider: Any = None,
    *,
    run_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Execute one pass of a canonical ALO's managerObj and return a Run Record.

    Field names follow docs/spec.md section 10 (State_before/State_after,
    manager_trace, jev_calls) plus a ``status`` field for the same "ok" /
    "input_error" / "error" convention the Draft 0.1 runtime already uses.
    """

    if not isinstance(document, Mapping):
        raise ManagerError("document must be an object")
    alo = document.get("alo")
    if not isinstance(alo, Mapping):
        raise ManagerError("document must contain an 'alo' object")
    if alo.get("spec_version") != "0.2":
        raise ManagerError("run_manager only supports canonical spec_version '0.2'")

    manager_obj = alo.get("managerObj")
    if not isinstance(manager_obj, Mapping):
        raise ManagerError("alo.managerObj must be an object")
    state_schema = alo.get("State")
    if not isinstance(state_schema, Mapping):
        raise ManagerError("alo.State must be an object")

    record: dict[str, Any] = {
        "run_id": run_id or str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "alo": {
            "id": alo.get("id"),
            "version": alo.get("version"),
            "canonical_hash": _canonical_hash(document),
        },
        "input": None,
        "State_before": None,
        "manager_trace": [],
        "jev_calls": [],
        "deterministic_calculations": [],
        "state_updates": [],
        "State_after": None,
        "output": None,
        "status": "ok",
    }

    declared_input_fields = _string_list(manager_obj.get("input", []))
    try:
        normalized_input = _normalize_input(declared_input_fields, input_data)
    except ManagerError as error:
        record["status"] = "input_error"
        record["error"] = str(error)
        return record
    record["input"] = normalized_input

    state = {key: copy.deepcopy(_field(field).get("value")) for key, field in state_schema.items()}
    record["State_before"] = copy.deepcopy(state)

    context: dict[str, Any] = {"input": normalized_input, "state": state, "jev": {}}

    process = manager_obj.get("process", [])
    if not isinstance(process, Sequence) or isinstance(process, (str, bytes, bytearray)):
        raise ManagerError("alo.managerObj.process must be an array")

    for raw_step in process:
        if not isinstance(raw_step, Mapping):
            raise ManagerError("each alo.managerObj.process step must be an object")
        step_id = raw_step.get("id")
        trace_entry: dict[str, Any] = {"step": step_id, "action": raw_step.get("action")}
        if "uses" in raw_step:
            trace_entry["subObj_used"] = raw_step["uses"]

        calculation = raw_step.get("calculation")
        if isinstance(calculation, Mapping):
            try:
                result = _run_calculation(step_id, calculation, context, provider, record)
            except ManagerError as error:
                record["status"] = "error"
                record["error"] = str(error)
                return record
            if result is None:
                trace_entry["calculation"] = "skipped (optional, no provider configured)"
            else:
                trace_entry["calculation"] = {"primitive": calculation["jev"]["type"], "result": result}
                context["jev"][step_id] = result
        else:
            trace_entry["kind"] = "language_defined"

        step_updates = raw_step.get("state_updates")
        if step_updates is not None:
            try:
                _apply_state_updates(step_updates, state, context, record)
            except ExpressionError as error:
                record["status"] = "error"
                record["error"] = f"managerObj.process[{step_id}].state_updates: {error}"
                return record

        record["manager_trace"].append(trace_entry)

    manager_level_updates = manager_obj.get("state_updates")
    if manager_level_updates is not None:
        try:
            _apply_state_updates(manager_level_updates, state, context, record)
        except ExpressionError as error:
            record["status"] = "error"
            record["error"] = f"managerObj.state_updates: {error}"
            return record

    record["State_after"] = state
    record["output"] = _build_output(manager_obj.get("output", []), state)
    return record


def _run_calculation(
    step_id: Any,
    calculation: Mapping[str, Any],
    context: Mapping[str, Any],
    provider: Any,
    record: dict[str, Any],
) -> dict[str, float] | None:
    jev = calculation.get("jev")
    if not isinstance(jev, Mapping):
        return None
    jev_type = jev.get("type")
    method = _JEV_METHOD.get(jev_type)
    if method is None:
        raise ManagerError(f"unknown Jev calculation type: {jev_type!r}")

    if provider is None:
        if calculation.get("provider") == "optional":
            return None
        raise ManagerError(
            f"managerObj.process[{step_id}] requires a Decision Provider for Jev {jev_type}"
        )

    question = jev.get("question", "")
    call_context = {"input": context["input"], "state": context["state"]}
    record["jev_calls"].append(
        {
            "step": step_id,
            "primitive": jev_type,
            "question": question,
            "request": call_context,
        }
    )
    call = getattr(provider, method)
    if jev_type == "Choice":
        options = jev.get("options", {})
        option_names = sorted(options) if isinstance(options, Mapping) else list(options)
        result = call(step_id, call_context, question, option_names)
    elif jev_type == "Score":
        scale = jev.get("scale", {})
        result = call(step_id, call_context, question, scale)
    else:
        result = call(step_id, call_context, question)
    record["jev_calls"][-1]["result"] = result
    record["jev_calls"][-1]["model"] = getattr(provider, "model", None)
    record["jev_calls"][-1]["provider"] = getattr(provider, "name", provider.__class__.__name__)
    return result


def _apply_state_updates(
    updates: Any,
    state: dict[str, Any],
    context: Mapping[str, Any],
    record: dict[str, Any],
) -> None:
    if not isinstance(updates, Sequence) or isinstance(updates, (str, bytes, bytearray)):
        raise ManagerError("state_updates must be an array")
    for update in updates:
        if not isinstance(update, Mapping):
            raise ManagerError("each state update must be an object")
        key = update.get("key")
        when = update.get("when")
        if when is not None:
            eval_context = dict(context)
            if not bool(evaluate(when, eval_context)):
                continue
        state[key] = update.get("value")
        record["state_updates"].append({"key": key, "value": update.get("value"), "when": when})


def _build_output(declared_fields: Any, state: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for field in _string_list(declared_fields):
        if field == "State":
            output[field] = copy.deepcopy(dict(state))
        elif field in state:
            output[field] = copy.deepcopy(state[field])
        else:
            output[field] = None
    return output


def _normalize_input(
    declared_fields: Sequence[str], input_data: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(input_data, Mapping):
        raise ManagerError("input must be an object")
    missing = [field for field in declared_fields if field not in input_data]
    if missing:
        raise ManagerError(f"missing required input field(s): {', '.join(missing)}")
    return dict(input_data)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item) for item in value]


def _field(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _canonical_hash(document: Mapping[str, Any]) -> str:
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
