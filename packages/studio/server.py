"""Dependency-free local web server for the Open ALO Studio.

API envelope convention: malformed requests use HTTP 400 with
``{"errors": ["..."]}``; semantic ALO errors use HTTP 200 with the same
error-only object. Successful responses retain the endpoint-specific payload
shape, and ``/api/validate`` always includes an ``errors`` array.

``/api/assist`` is optional: it requires the caller to supply their own
``model``/``api_key``/``base_url`` for an OpenAI-compatible endpoint. The key
is forwarded only to that endpoint for the single request and is never
stored or logged by Studio. No other route ever requires it.
"""

from __future__ import annotations

import json
import mimetypes
import tempfile
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from packages.compiler import CompileError, MermaidError, compile_alo, render_mermaid, render_svg
from packages.core import LoadError, load_document, validate_alo
from packages.providers import MockDecisionProvider, ProviderError
from packages.runtime import run as run_alo
from packages.studio.assistant import AssistantError, draft_alo


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_STATIC_ROOT = Path(__file__).resolve().parent / "static"
_MAX_BODY_BYTES = 2 * 1024 * 1024


class StudioServer(ThreadingHTTPServer):
    """Threaded HTTP server bound to localhost by default."""

    allow_reuse_address = True

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.repository_root = _REPOSITORY_ROOT
        self.static_root = _STATIC_ROOT.resolve()
        super().__init__((host, port), _StudioRequestHandler)


def serve(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    open_browser: bool = False,
) -> ThreadingHTTPServer:
    """Create, optionally open, and return a configured Studio server.

    The caller owns the server lifecycle and may call ``serve_forever``.
    """

    server = StudioServer(host, port)
    if open_browser:
        webbrowser.open(_server_url(server))
    return server


class _StudioRequestHandler(BaseHTTPRequestHandler):
    server: StudioServer

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/examples":
            self._send_json(HTTPStatus.OK, _examples(self.server.repository_root))
            return
        if path.startswith("/api/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"errors": ["route not found"]})
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = urllib.parse.urlsplit(self.path).path
        routes = {
            "/api/validate": self._post_validate,
            "/api/graph": self._post_graph,
            "/api/run": self._post_run,
            "/api/assist": self._post_assist,
        }
        handler = routes.get(path)
        if handler is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"errors": ["route not found"]})
            return
        try:
            body = self._read_json_body()
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})
            return
        handler(body)

    def _post_validate(self, body: Any) -> None:
        try:
            source = _source_from_body(body)
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})
            return
        document, errors = _load_and_validate_text(source)
        self._send_json(
            HTTPStatus.OK,
            {"valid": document is not None and not errors, "errors": errors},
        )

    def _post_graph(self, body: Any) -> None:
        try:
            source = _source_from_body(body)
            direction = body.get("direction", "TD")
            if not isinstance(direction, str):
                raise ValueError("direction must be a string")
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})
            return
        document, errors = _load_and_validate_text(source)
        if errors or document is None:
            self._send_json(HTTPStatus.OK, {"errors": errors})
            return
        try:
            graph = compile_alo(document)
            mermaid = render_mermaid(graph, direction=direction)
            svg = render_svg(graph, direction=direction)
        except (CompileError, MermaidError, ValueError) as error:
            self._send_json(HTTPStatus.OK, {"errors": [str(error)]})
            return
        self._send_json(
            HTTPStatus.OK,
            {"graph": graph, "mermaid": mermaid, "svg": svg},
        )

    def _post_run(self, body: Any) -> None:
        try:
            source = _source_from_body(body)
            input_data = body.get("input", {})
            responses = body.get("responses", {})
            if not isinstance(input_data, dict):
                raise ValueError("input must be an object")
            if not isinstance(responses, dict):
                raise ValueError("responses must be an object")
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})
            return
        document, errors = _load_and_validate_text(source)
        if errors or document is None:
            self._send_json(HTTPStatus.OK, {"errors": errors})
            return
        try:
            record = run_alo(document, input_data, MockDecisionProvider(responses))
        except (ValueError, TypeError, KeyError) as error:
            self._send_json(HTTPStatus.OK, {"errors": [str(error)]})
            return
        self._send_json(HTTPStatus.OK, record)

    def _post_assist(self, body: Any) -> None:
        description = body.get("description")
        model = body.get("model")
        if not isinstance(description, str) or not description.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": ["description must be a non-empty string"]})
            return
        if not isinstance(model, str) or not model.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": ["model must be a non-empty string"]})
            return
        api_key = body.get("api_key")
        base_url = body.get("base_url", "https://api.openai.com/v1")
        if api_key is not None and not isinstance(api_key, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": ["api_key must be a string"]})
            return
        if not isinstance(base_url, str) or not base_url.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"errors": ["base_url must be a non-empty string"]})
            return
        try:
            source = draft_alo(description, model=model, api_key=api_key, base_url=base_url)
        except (AssistantError, ProviderError) as error:
            self._send_json(HTTPStatus.OK, {"errors": [str(error)]})
            return
        document, errors = _load_and_validate_text(source)
        self._send_json(
            HTTPStatus.OK,
            {"source": source, "valid": document is not None and not errors, "errors": errors},
        )

    def _read_json_body(self) -> Any:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as error:
            raise ValueError("Content-Length must be an integer") from error
        if length < 0 or length > _MAX_BODY_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("request body is incomplete")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid JSON request body: {error}") from error
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def _serve_static(self, path: str) -> None:
        relative = urllib.parse.unquote(path).lstrip("/")
        if not relative:
            relative = "index.html"
        candidate = (self.server.static_root / relative).resolve()
        try:
            candidate.relative_to(self.server.static_root)
        except ValueError:
            self._send_json(HTTPStatus.NOT_FOUND, {"errors": ["file not found"]})
            return
        if not candidate.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"errors": ["file not found"]})
            return
        try:
            content = candidate.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"errors": ["file not found"]})
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, payload: Any) -> None:
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep normal API use quiet; errors are still represented in responses.
        return


def _source_from_body(body: Any) -> str:
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    source = body.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")
    return source


def _load_and_validate_text(source: str) -> tuple[dict[str, Any] | None, list[str]]:
    suffix = ".json" if source.lstrip().startswith(("{", "[")) else ".yaml"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, encoding="utf-8", delete=False
        ) as temporary:
            temporary.write(source)
            temporary_path = temporary.name
        document = load_document(temporary_path)
    except (LoadError, OSError) as error:
        return None, [str(error)]
    finally:
        if temporary_path is not None:
            try:
                Path(temporary_path).unlink()
            except OSError:
                pass
    errors = validate_alo(document)
    return (document if not errors else None), errors


def _examples(repository_root: Path) -> list[dict[str, str]]:
    examples_root = repository_root / "examples"
    results: list[dict[str, str]] = []
    if not examples_root.is_dir():
        return results
    for directory in sorted(examples_root.iterdir(), key=lambda item: item.name):
        if not directory.is_dir():
            continue
        for filename in ("alo.yaml", "alo.json"):
            path = directory / filename
            if not path.is_file():
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:
                continue
            results.append(
                {
                    "id": directory.name,
                    "path": path.relative_to(repository_root).as_posix(),
                    "source": source,
                }
            )
    return results


def _server_url(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"
