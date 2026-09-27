"""Validation for the canonical ALO object model, independent of a
third-party JSON Schema package.

An ALO is ``mainObj`` + ``subObjList`` + ``State`` + ``managerObj`` (see
docs/spec.md and docs/implementation-correction.md); this validates that
shape for ``alo.spec_version == "0.2"`` and rejects anything else.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
JEV_CALCULATION_TYPES = {"Noul", "Choice", "Score"}


class ValidationError(ValueError):
    """Raised when an ALO document does not conform to its declared spec_version."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def validate_alo(document: Mapping[str, Any]) -> list[str]:
    """Return validation errors; return an empty list for a valid ALO."""

    errors: list[str] = []
    if not isinstance(document, Mapping):
        return ["document must be an object"]
    alo = document.get("alo")
    if not isinstance(alo, Mapping):
        return ["alo must be an object"]

    return _validate_canonical_object_model(alo)


def _validate_canonical_object_model(alo: Mapping[str, Any]) -> list[str]:
    """Validate the canonical Draft 0.2 object model: mainObj/subObjList/State/managerObj."""

    errors: list[str] = []
    required = ("spec_version", "id", "version", "mainObj", "subObjList", "State", "managerObj")
    for field in required:
        if field not in alo:
            errors.append(f"alo.{field} is required")
    if alo.get("spec_version") != "0.2":
        errors.append("alo.spec_version must be '0.2'")
    for field in ("id", "version"):
        if field in alo and not _non_empty_string(alo[field]):
            errors.append(f"alo.{field} must be a non-empty string")
    if "id" in alo:
        _identifier(alo["id"], "alo.id", errors)

    main_obj = _object(alo.get("mainObj"), "alo.mainObj", errors)
    if main_obj:
        _identifier(main_obj.get("id"), "alo.mainObj.id", errors)
        if not _non_empty_string(main_obj.get("purpose")):
            errors.append("alo.mainObj.purpose must be a non-empty string")
        if "version" in main_obj and not _non_empty_string(main_obj["version"]):
            errors.append("alo.mainObj.version must be a non-empty string")
        _responsibilities(
            main_obj.get("responsibilities"), "alo.mainObj.responsibilities", errors
        )

    sub_obj_list = _array(alo.get("subObjList"), "alo.subObjList", errors)
    sub_obj_ids: set[str] = set()
    for index, sub_obj in enumerate(sub_obj_list):
        path = f"alo.subObjList[{index}]"
        sub_obj = _object(sub_obj, path, errors)
        if not sub_obj:
            continue
        sub_obj_id = sub_obj.get("id")
        _identifier(sub_obj_id, f"{path}.id", errors)
        if isinstance(sub_obj_id, str):
            if sub_obj_id in sub_obj_ids:
                errors.append(f"duplicate subObj id: {sub_obj_id}")
            sub_obj_ids.add(sub_obj_id)
        if not _non_empty_string(sub_obj.get("purpose")):
            errors.append(f"{path}.purpose must be a non-empty string")
        if "version" in sub_obj and not _non_empty_string(sub_obj["version"]):
            errors.append(f"{path}.version must be a non-empty string")
        _responsibilities(sub_obj.get("responsibilities"), f"{path}.responsibilities", errors)

    state = _object(alo.get("State"), "alo.State", errors)
    for key, field in state.items():
        _identifier(key, f"alo.State.{key}", errors)
        field = _object(field, f"alo.State.{key}", errors)
        if field and "type" not in field:
            errors.append(f"alo.State.{key}.type is required")
        elif field and not _non_empty_string(field.get("type")):
            errors.append(f"alo.State.{key}.type must be a non-empty string")
        if field and "value" not in field:
            errors.append(f"alo.State.{key}.value is required")

    manager_obj = _object(alo.get("managerObj"), "alo.managerObj", errors)
    if manager_obj:
        _non_empty_string_array(
            manager_obj.get("input"), "alo.managerObj.input", errors, min_items=1
        )
        _non_empty_string_array(
            manager_obj.get("output"), "alo.managerObj.output", errors, min_items=1
        )
        process = _array(manager_obj.get("process"), "alo.managerObj.process", errors)
        if not process:
            errors.append("alo.managerObj.process must have at least one step")
        step_ids: set[str] = set()
        for index, step in enumerate(process):
            path = f"alo.managerObj.process[{index}]"
            step = _object(step, path, errors)
            if not step:
                continue
            step_id = step.get("id")
            _identifier(step_id, f"{path}.id", errors)
            if isinstance(step_id, str):
                if step_id in step_ids:
                    errors.append(f"duplicate managerObj process step id: {step_id}")
                step_ids.add(step_id)
            if not _non_empty_string(step.get("action")):
                errors.append(f"{path}.action must be a non-empty string")
            if "calculation" in step:
                _jev_calculation(step["calculation"], f"{path}.calculation", errors)
            if "state_updates" in step:
                _state_updates(step["state_updates"], f"{path}.state_updates", errors, state)
        if "state_updates" in manager_obj:
            _state_updates(
                manager_obj["state_updates"], "alo.managerObj.state_updates", errors, state
            )

    return errors


def _responsibilities(value: Any, path: str, errors: list[str]) -> None:
    if value is None:
        return
    for index, item in enumerate(_array(value, path, errors)):
        if not _non_empty_string(item):
            errors.append(f"{path}[{index}] must be a non-empty string")


def _non_empty_string_array(
    value: Any, path: str, errors: list[str], *, min_items: int = 0
) -> None:
    items = _array(value, path, errors)
    if len(items) < min_items:
        errors.append(f"{path} must have at least {min_items} item(s)")
    for index, item in enumerate(items):
        if not _non_empty_string(item):
            errors.append(f"{path}[{index}] must be a non-empty string")


def _jev_calculation(value: Any, path: str, errors: list[str]) -> None:
    calculation = _object(value, path, errors)
    if not calculation:
        return
    if "provider" in calculation and not _non_empty_string(calculation["provider"]):
        errors.append(f"{path}.provider must be a non-empty string")
    if "jev" not in calculation:
        return
    jev = _object(calculation["jev"], f"{path}.jev", errors)
    if not jev:
        return
    if jev.get("type") not in JEV_CALCULATION_TYPES:
        errors.append(f"{path}.jev.type must be one of {sorted(JEV_CALCULATION_TYPES)}")
    if not _non_empty_string(jev.get("question")):
        errors.append(f"{path}.jev.question must be a non-empty string")


def _state_updates(
    value: Any, path: str, errors: list[str], state: Mapping[str, Any]
) -> None:
    for index, update in enumerate(_array(value, path, errors)):
        item_path = f"{path}[{index}]"
        update = _object(update, item_path, errors)
        if not update:
            continue
        key = update.get("key")
        _identifier(key, f"{item_path}.key", errors)
        if isinstance(key, str) and key not in state:
            errors.append(f"{item_path}.key is not declared in alo.State: {key}")
        if "value" not in update:
            errors.append(f"{item_path}.value is required")
        if "when" in update and not _non_empty_string(update["when"]):
            errors.append(f"{item_path}.when must be a non-empty string")


def ensure_valid(document: Mapping[str, Any]) -> None:
    errors = validate_alo(document)
    if errors:
        raise ValidationError(errors)


def _object(value: Any, path: str, errors: list[str]) -> Mapping[str, Any]:
    if value is None:
        errors.append(f"{path} is required")
        return {}
    if not isinstance(value, Mapping):
        errors.append(f"{path} must be an object")
        return {}
    return value


def _array(value: Any, path: str, errors: list[str]) -> Sequence[Any]:
    if value is None:
        errors.append(f"{path} is required")
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        errors.append(f"{path} must be an array")
        return []
    return value


def _identifier(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        errors.append(f"{path} must match ^[A-Za-z][A-Za-z0-9_-]*$")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)
