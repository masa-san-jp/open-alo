"""ALO validation independent of a third-party JSON Schema package.

Dispatches on ``alo.spec_version``: ``"0.2"`` is the canonical object model
(``mainObj``/``subObjList``/``State``/``managerObj`` -- see docs/spec.md and
docs/implementation-correction.md). ``"0.1"`` is the superseded workflow-DSL
shape, kept only so the legacy example (``examples/minimal/``) still
validates during migration; it is not canonical (see AGENTS.md).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
FIELD_TYPES = {"string", "integer", "number", "boolean", "object", "array", "enum"}
DECISION_TYPES = {"binary", "categorical", "scalar"}
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

    if alo.get("spec_version") == "0.2":
        return _validate_canonical_object_model(alo)
    return _validate_legacy_workflow(alo)


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


def _validate_legacy_workflow(alo: Mapping[str, Any]) -> list[str]:
    """Validate the superseded Draft 0.1 workflow-DSL shape (legacy only)."""

    errors: list[str] = []

    required = (
        "spec_version",
        "id",
        "version",
        "purpose",
        "inputs",
        "state_schema",
        "decisions",
        "transition_rules",
        "outputs",
    )
    for field in required:
        if field not in alo:
            errors.append(f"alo.{field} is required")
    if alo.get("spec_version") != "0.1":
        errors.append("alo.spec_version must be '0.1'")
    for field in ("id", "version", "purpose"):
        if field in alo and not _non_empty_string(alo[field]):
            errors.append(f"alo.{field} must be a non-empty string")
    if "threshold_version" in alo and not _non_empty_string(alo["threshold_version"]):
        errors.append("alo.threshold_version must be a non-empty string")
    if "id" in alo:
        _identifier(alo["id"], "alo.id", errors)

    inputs = _object(alo.get("inputs"), "alo.inputs", errors)
    for name, field in inputs.items():
        _identifier(name, f"alo.inputs.{name}", errors)
        _field(field, f"alo.inputs.{name}", errors, require_input=True)

    state = _object(alo.get("state_schema"), "alo.state_schema", errors)
    for name, field in state.items():
        _identifier(name, f"alo.state_schema.{name}", errors)
        _field(field, f"alo.state_schema.{name}", errors, require_state=True)

    outputs = _object(alo.get("outputs"), "alo.outputs", errors)
    for name, field in outputs.items():
        _identifier(name, f"alo.outputs.{name}", errors)
        _field(field, f"alo.outputs.{name}", errors)

    decisions = _array(alo.get("decisions"), "alo.decisions", errors)
    decision_ids: set[str] = set()
    for index, decision in enumerate(decisions):
        path = f"alo.decisions[{index}]"
        if not isinstance(decision, Mapping):
            errors.append(f"{path} must be an object")
            continue
        decision_id = decision.get("id")
        _identifier(decision_id, f"{path}.id", errors)
        if isinstance(decision_id, str) and decision_id in decision_ids:
            errors.append(f"duplicate decision id: {decision_id}")
        if isinstance(decision_id, str):
            decision_ids.add(decision_id)
        decision_type = decision.get("type")
        if decision_type not in DECISION_TYPES:
            errors.append(f"{path}.type must be binary, categorical, or scalar")
        reads = _array(decision.get("reads"), f"{path}.reads", errors)
        for read_index, reference in enumerate(reads):
            if not _non_empty_string(reference):
                errors.append(f"{path}.reads[{read_index}] must be a string")
        if not _non_empty_string(decision.get("question")):
            errors.append(f"{path}.question must be a non-empty string")
        if decision_type == "categorical":
            options = _object(decision.get("options"), f"{path}.options", errors)
            if not options:
                errors.append(f"{path}.options must contain at least one option")
            for option in options:
                _identifier(option, f"{path}.options.{option}", errors)
        if decision_type == "scalar":
            scale = _object(decision.get("scale"), f"{path}.scale", errors)
            for bound in ("min", "max"):
                if not isinstance(scale.get(bound), (int, float)) or isinstance(
                    scale.get(bound), bool
                ):
                    errors.append(f"{path}.scale.{bound} must be a number")

    raw_stop_conditions = alo.get("stop_conditions")
    declared_stop_conditions: set[str] = set()
    if raw_stop_conditions is not None:
        for index, condition in enumerate(
            _array(raw_stop_conditions, "alo.stop_conditions", errors)
        ):
            if _non_empty_string(condition):
                declared_stop_conditions.add(condition)
            else:
                errors.append(f"alo.stop_conditions[{index}] must be a non-empty string")

    rules = _array(alo.get("transition_rules"), "alo.transition_rules", errors)
    rule_ids: set[str] = set()
    priorities: set[int] = set()
    for index, rule in enumerate(rules):
        path = f"alo.transition_rules[{index}]"
        if not isinstance(rule, Mapping):
            errors.append(f"{path} must be an object")
            continue
        rule_id = rule.get("id")
        _identifier(rule_id, f"{path}.id", errors)
        if isinstance(rule_id, str) and rule_id in rule_ids:
            errors.append(f"duplicate transition rule id: {rule_id}")
        if isinstance(rule_id, str):
            rule_ids.add(rule_id)
        priority = rule.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool):
            errors.append(f"{path}.priority must be an integer")
        elif priority in priorities:
            errors.append(f"duplicate transition rule priority: {priority}")
        else:
            priorities.add(priority)
        if not _non_empty_string(rule.get("when")):
            errors.append(f"{path}.when must be a non-empty string")
        assignments = _object(rule.get("set"), f"{path}.set", errors)
        for target in assignments:
            _identifier(target, f"{path}.set.{target}", errors)
            if target not in state and target not in outputs:
                errors.append(f"{path}.set.{target} is not a state or output field")
        stop_condition = rule.get("stop_condition")
        if stop_condition is not None:
            if not _non_empty_string(stop_condition):
                errors.append(f"{path}.stop_condition must be a non-empty string")
            elif stop_condition not in declared_stop_conditions:
                errors.append(
                    f"{path}.stop_condition must be declared in alo.stop_conditions: "
                    f"{stop_condition}"
                )

    _optional_string_array(alo.get("invariants"), "alo.invariants", errors)
    return errors


def ensure_valid(document: Mapping[str, Any]) -> None:
    errors = validate_alo(document)
    if errors:
        raise ValidationError(errors)


def _field(
    value: Any,
    path: str,
    errors: list[str],
    require_input: bool = False,
    require_state: bool = False,
) -> None:
    field = _object(value, path, errors)
    field_type = field.get("type")
    if field_type not in FIELD_TYPES:
        errors.append(f"{path}.type must be one of {sorted(FIELD_TYPES)}")
    if require_input and not isinstance(field.get("required"), bool):
        errors.append(f"{path}.required must be boolean")
    if require_state:
        if "initial" not in field:
            errors.append(f"{path}.initial is required")
        if not _non_empty_string(field.get("updated_by")):
            errors.append(f"{path}.updated_by must be a non-empty string")
    if field_type == "enum" and not isinstance(field.get("values"), list):
        errors.append(f"{path}.values must be an array for enum fields")
    if field_type == "array" and not isinstance(field.get("items"), Mapping):
        errors.append(f"{path}.items must be an object for array fields")


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


def _optional_string_array(value: Any, path: str, errors: list[str]) -> None:
    if value is None:
        return
    for index, item in enumerate(_array(value, path, errors)):
        if not _non_empty_string(item):
            errors.append(f"{path}[{index}] must be a non-empty string")


def _identifier(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        errors.append(f"{path} must match ^[A-Za-z][A-Za-z0-9_-]*$")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)
