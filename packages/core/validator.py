"""Draft 0.1 validation independent of a third-party JSON Schema package."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
FIELD_TYPES = {"string", "integer", "number", "boolean", "object", "array", "enum"}
DECISION_TYPES = {"binary", "categorical", "scalar"}


class ValidationError(ValueError):
    """Raised when an ALO document does not conform to Draft 0.1."""

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
