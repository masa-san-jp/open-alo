"""Render a canonical Draft 0.2 ALO document as an ALO Prompt (Layer A).

Per docs/spec.md section 5: "The structured YAML form and the rendered
prompt must express the same ALO semantics." This renders the document's
actual declared `mainObj`, `subObjList`, `State`, and `managerObj.process`
steps -- not a generic, content-free boilerplate description of a manager
loop -- so a reader (human or LLM) gets the same information the structured
form encodes.

This is pure text generation: no network access, no Decision Provider, no
reasoning. It is deterministic in the declared document order (Python
preserves mapping/list order from the loaded YAML/JSON).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class PromptError(ValueError):
    """Raised when a document cannot be rendered as an ALO Prompt."""


def render_prompt(document: Mapping[str, Any]) -> str:
    """Render a canonical (spec_version 0.2) ALO document as an ALO Prompt."""

    if not isinstance(document, Mapping):
        raise PromptError("document must be an object")
    alo = document.get("alo")
    if not isinstance(alo, Mapping):
        raise PromptError("document must contain an 'alo' object")
    if alo.get("spec_version") != "0.2":
        raise PromptError("render_prompt only supports canonical spec_version '0.2'")

    main_obj = _require_mapping(alo.get("mainObj"), "alo.mainObj")
    sub_obj_list = _require_sequence(alo.get("subObjList"), "alo.subObjList")
    state = _require_mapping(alo.get("State"), "alo.State")
    manager_obj = _require_mapping(alo.get("managerObj"), "alo.managerObj")

    lines: list[str] = [
        "# ALO",
        "",
        "You are operating the following Abstract Language Object.",
        "",
        "## mainObj",
    ]
    lines.extend(_object_lines(main_obj, "alo.mainObj"))

    lines.append("")
    lines.append("## subObjList")
    if not sub_obj_list:
        lines.append("")
        lines.append("(no sub-objects declared)")
    for index, sub_obj in enumerate(sub_obj_list):
        sub_obj = _require_mapping(sub_obj, f"alo.subObjList[{index}]")
        sub_obj_id = sub_obj.get("id", f"sub_{index}")
        lines.append("")
        lines.append(f"### {sub_obj_id}")
        lines.extend(_object_lines(sub_obj, f"alo.subObjList[{index}]", skip_id=True))

    lines.append("")
    lines.append("## State")
    if not state:
        lines.append("")
        lines.append("(no State declared)")
    for key, field in state.items():
        field = field if isinstance(field, Mapping) else {}
        lines.append(f"- {key}: {field.get('value')!r}")

    lines.append("")
    lines.append("## managerObj")
    lines.append("")
    manager_input = manager_obj.get("input", [])
    if manager_input:
        lines.append(f"Input fields: {', '.join(str(item) for item in manager_input)}")
        lines.append("")
    lines.append("For every input, perform these steps in order:")
    lines.append("")
    process = _require_sequence(manager_obj.get("process"), "alo.managerObj.process")
    for index, step in enumerate(process, start=1):
        step = _require_mapping(step, f"alo.managerObj.process[{index - 1}]")
        action = str(step.get("action", "")).strip()
        lines.append(f"{index}. {action}")
        calculation = step.get("calculation")
        if isinstance(calculation, Mapping):
            jev = calculation.get("jev")
            if isinstance(jev, Mapping):
                jev_type = jev.get("type", "")
                question = jev.get("question", "")
                lines.append(
                    f"   - Calculation: Jev {jev_type} -- {question!r}"
                )
    manager_output = manager_obj.get("output", [])
    if manager_output:
        lines.append("")
        lines.append(f"Output fields: {', '.join(str(item) for item in manager_output)}")

    lines.append("")
    lines.append("## Input")
    lines.append("<runtime input>")
    return "\n".join(lines) + "\n"


def _object_lines(
    obj: Mapping[str, Any], path: str, *, skip_id: bool = False
) -> list[str]:
    lines: list[str] = []
    if not skip_id and "id" in obj:
        lines.append(f"- id: {obj['id']}")
    if "purpose" in obj:
        purpose = str(obj["purpose"]).strip()
        lines.append(f"- purpose: {purpose}")
    responsibilities = obj.get("responsibilities")
    if isinstance(responsibilities, Sequence) and not isinstance(
        responsibilities, (str, bytes, bytearray)
    ):
        if responsibilities:
            lines.append("- responsibilities:")
            for item in responsibilities:
                lines.append(f"  - {item}")
    return lines


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PromptError(f"{path} must be an object")
    return value


def _require_sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PromptError(f"{path} must be an array")
    return value
