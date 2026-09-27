"""Command-line interface for Open ALO: validate, graph, run, and test."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from packages.compiler import CompileError, MermaidError, compile_alo, render_mermaid
from packages.core import LoadError, ValidationError, load_document, validate_alo
from packages.packaging import (
    PackagingError,
    badge_markdown,
    build_package,
    install_from_git,
    load_manifest,
    load_registry,
    search_registry,
    validate_manifest,
)
from packages.providers import MockDecisionProvider
from packages.runtime import run as run_alo
from packages.studio import StudioServer

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

    package_parser = subparsers.add_parser("package", help="Build and inspect ALO packages")
    package_subparsers = package_parser.add_subparsers(dest="package_command")

    package_build_parser = package_subparsers.add_parser(
        "build", help="Validate and build a plain-directory ALO package"
    )
    package_build_parser.add_argument("source_dir", help="Package source directory")
    package_build_parser.add_argument(
        "--out", required=True, help="Directory in which to create the package"
    )
    package_build_parser.set_defaults(handler=_cmd_package_build)

    package_install_parser = package_subparsers.add_parser(
        "install", help="Install an ALO package from a Git repository"
    )
    package_install_parser.add_argument("repo_url_or_path", help="Git URL or local repository path")
    package_install_parser.add_argument(
        "--dest", required=True, help="Directory in which to install the package"
    )
    package_install_parser.add_argument("--ref", default="HEAD", help="Git ref (default: HEAD)")
    package_install_parser.add_argument("--subdir", help="Package subdirectory within the repository")
    package_install_parser.set_defaults(handler=_cmd_package_install)

    package_search_parser = package_subparsers.add_parser(
        "search", help="Search a local/offline registry index"
    )
    package_search_parser.add_argument("registry_path", help="Path to a registry JSON file")
    package_search_parser.add_argument("query", help="Case-insensitive name or description query")
    package_search_parser.set_defaults(handler=_cmd_package_search)

    package_badge_parser = package_subparsers.add_parser(
        "badge", help="Generate an Open ALO compatibility badge"
    )
    package_badge_parser.add_argument(
        "manifest_or_alo_path", help="Path to alo-package.json or an ALO YAML/JSON file"
    )
    package_badge_parser.set_defaults(handler=_cmd_package_badge)

    studio_parser = subparsers.add_parser(
        "studio", help="Launch the local web Studio"
    )
    studio_parser.add_argument(
        "--host", default="127.0.0.1", help="Studio bind host (default: 127.0.0.1)"
    )
    studio_parser.add_argument(
        "--port", type=int, default=0, help="Studio port (default: 0, choose a free port)"
    )
    studio_parser.add_argument(
        "--no-browser", action="store_true", help="Do not open the Studio in a browser"
    )
    studio_parser.set_defaults(handler=_cmd_studio)

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


def _cmd_package_build(args: argparse.Namespace) -> int:
    try:
        package_path = build_package(args.source_dir, args.out)
    except PackagingError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(package_path)
    return 0


def _cmd_package_install(args: argparse.Namespace) -> int:
    try:
        package_path = install_from_git(
            args.repo_url_or_path,
            args.dest,
            ref=args.ref,
            subdir=args.subdir,
        )
    except PackagingError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(package_path)
    return 0


def _cmd_package_search(args: argparse.Namespace) -> int:
    try:
        registry = load_registry(args.registry_path)
        matches = search_registry(registry, args.query)
    except PackagingError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(matches, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_package_badge(args: argparse.Namespace) -> int:
    try:
        spec_version = _load_badge_spec_version(args.manifest_or_alo_path)
    except (LoadError, PackagingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(badge_markdown(spec_version))
    return 0


def _load_badge_spec_version(path: str) -> str:
    """Load a spec version from either a package manifest or an ALO document."""

    try:
        value = load_manifest(path)
    except PackagingError as manifest_error:
        try:
            document = load_document(path)
        except LoadError:
            raise manifest_error
        errors = validate_alo(document)
        if errors:
            raise PackagingError("invalid ALO document: " + "; ".join(errors))
        return str(document["alo"]["spec_version"])

    if "alo" in value:
        errors = validate_alo(value)
        if errors:
            raise PackagingError("invalid ALO document: " + "; ".join(errors))
        return str(value["alo"]["spec_version"])
    errors = validate_manifest(value)
    if errors:
        raise PackagingError("invalid package manifest: " + "; ".join(errors))
    return str(value["spec_version"])


def _cmd_studio(args: argparse.Namespace) -> int:
    server = StudioServer(args.host, args.port)
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}/"
    print(f"Studio running at {url} (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # shutdown() must be called from another thread while serve_forever is
        # active; closing the listening socket is the safe CLI-thread cleanup.
        server.server_close()
    return 0


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
