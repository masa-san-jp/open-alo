"""Command-line interface for Open ALO: validate, graph, run, and test."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from packages.compiler import CompileError, MermaidError, compile_alo, render_mermaid
from packages.core import LoadError, ValidationError, load_document, validate_alo
from packages.providers import MockDecisionProvider
from packages.runtime import run as run_alo

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "handler", None) is None:
        parser.print_help()
        return 1
    return args.handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alo", description="Open ALO reference CLI")
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate an ALO source file against Draft 0.1"
    )
    validate_parser.add_argument("path", help="Path to an ALO YAML or JSON file")
    validate_parser.set_defaults(handler=_cmd_validate)

    graph_parser = subparsers.add_parser(
        "graph", help="Compile an ALO source file and render it as Mermaid"
    )
    graph_parser.add_argument("path", help="Path to an ALO YAML or JSON file")
    graph_parser.add_argument(
        "--direction", default="TD", help="Mermaid flowchart direction (default: TD)"
    )
    graph_parser.add_argument("--out", help="Write the diagram to this file instead of stdout")
    graph_parser.set_defaults(handler=_cmd_graph)

    run_parser = subparsers.add_parser(
        "run", help="Execute an ALO source file once with the mock Decision Provider"
    )
    run_parser.add_argument("path", help="Path to an ALO YAML or JSON file")
    run_parser.add_argument("--input", required=True, help="Path to a JSON input file")
    run_parser.add_argument(
        "--responses", help="Path to a JSON file of mock Decision Provider responses"
    )
    run_parser.add_argument("--out", help="Write the Run Record to this file instead of stdout")
    run_parser.set_defaults(handler=_cmd_run)

    test_parser = subparsers.add_parser(
        "test", help="Run the declared test cases for an example directory"
    )
    test_parser.add_argument(
        "path", help="Directory containing an ALO source file and tests.json"
    )
    test_parser.set_defaults(handler=_cmd_test)

    return parser


def _load_and_validate(path: str) -> tuple[dict[str, Any] | None, int]:
    try:
        document = load_document(path)
    except LoadError as error:
        print(f"error: {error}", file=sys.stderr)
        return None, 1
    errors = validate_alo(document)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return None, 1
    return document, 0


def _cmd_validate(args: argparse.Namespace) -> int:
    document, status = _load_and_validate(args.path)
    if document is None:
        return status
    print(f"{args.path}: valid")
    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    document, status = _load_and_validate(args.path)
    if document is None:
        return status
    try:
        graph = compile_alo(document)
        diagram = render_mermaid(graph, direction=args.direction)
    except (CompileError, MermaidError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).write_text(diagram, encoding="utf-8")
    else:
        print(diagram, end="")
    return 0


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cmd_run(args: argparse.Namespace) -> int:
    document, status = _load_and_validate(args.path)
    if document is None:
        return status
    try:
        input_data = _read_json(args.input)
        responses = _read_json(args.responses) if args.responses else {}
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    provider = MockDecisionProvider(responses)
    try:
        record = run_alo(document, input_data, provider)
    except ValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 1 if record["status"] in ("input_error", "error") else 0


def _cmd_test(args: argparse.Namespace) -> int:
    directory = Path(args.path)
    alo_path = directory / "alo.yaml"
    if not alo_path.is_file():
        alo_path = directory / "alo.json"
    tests_path = directory / "tests.json"

    document, status = _load_and_validate(str(alo_path))
    if document is None:
        return status
    try:
        suite = _read_json(str(tests_path))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    cases = suite.get("cases", [])
    failures = 0
    for case in cases:
        name = case.get("name", "<unnamed>")
        provider = MockDecisionProvider(case.get("provider", {}))
        try:
            record = run_alo(document, case.get("input", {}), provider)
        except ValidationError as error:
            failures += 1
            print(f"FAIL {name}: {error}")
            continue
        mismatches = _diff_expected(record, case.get("expected", {}))
        if mismatches:
            failures += 1
            print(f"FAIL {name}: {'; '.join(mismatches)}")
        else:
            print(f"PASS {name}")

    total = len(cases)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


def _diff_expected(record: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, value in expected.items():
        actual = record.get(key)
        if isinstance(value, Mapping) and isinstance(actual, Mapping):
            for sub_key, sub_value in value.items():
                actual_value = actual.get(sub_key)
                if actual_value != sub_value:
                    mismatches.append(
                        f"{key}.{sub_key} expected {sub_value!r} got {actual_value!r}"
                    )
        elif actual != value:
            mismatches.append(f"{key} expected {value!r} got {actual!r}")
    return mismatches
