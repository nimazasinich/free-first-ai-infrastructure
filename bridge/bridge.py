#!/usr/bin/env python3
"""Private, authenticated AIStudio2API transport for the approved model allowlist."""
from contextlib import ExitStack, contextmanager, suppress
from functools import partial
from http.client import HTTPConnection, HTTPException, IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
from selectors import DefaultSelector, EVENT_READ
import socket
from threading import Event, Thread
from time import monotonic


MODEL = "gemini-3.8-flash"
PILOT_MODEL = "gemini-3.5-flash-lite"
MODELS = frozenset({MODEL, PILOT_MODEL})
POST_ROUTES = {"/v1/chat/completions", "/v1/responses"}
MAX_BODY = 6 * 1024 * 1024
MAX_REPLY = 16 * 1024 * 1024
ROUTER_RETRY_CODES = {502, 503, 504}
UPSTREAM_IO_TIMEOUT = 115


class Bridge(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, upstream, credential, **kwargs):
        self.upstream = upstream
        self.authorization = ("Bearer " + credential).encode()
        super().__init__(*args, **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(130)

    def log_message(self, format, *args):
        pass

    def _json(self, code, data, retry_after=None):
        body = json.dumps(data, separators=(",", ":")).encode()
        self._headers(code, "application/json", length=len(body), retry_after=retry_after)
        self.wfile.write(body)

    def _error(self, code, message, retry_after=None):
        self._json(code, {"error": {"message": message, "type": "bridge_error"}}, retry_after)

    def _headers(self, code, content_type, *, length=None, retry_after=None):
        self.close_connection = True
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        if retry_after is not None:
            self.send_header("Retry-After", retry_after)
        if length is None:
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def _authorized(self):
        values = self.headers.get_all("Authorization", [])
        if len(values) == 1 and hmac.compare_digest(values[0].encode(), self.authorization):
            return True
        self._error(401, "Invalid upstream credential")
        return False

    def do_GET(self):
        if self.path != "/v1/models":
            self._error(404, "Route unavailable")
        elif self._authorized():
            self._forward()

    def do_POST(self):
        if self.path not in POST_ROUTES:
            self._error(404, "Route unavailable")
            return
        if not self._authorized():
            return

        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") is not None or len(lengths) != 1:
            self._error(400, "Expected one Content-Length header")
            return
        try:
            length = int(lengths[0])
        except ValueError:
            self._error(400, "Invalid Content-Length")
            return
        if not 0 < length <= MAX_BODY:
            self._error(413, "Body size outside allowed range")
            return
        if self.headers.get_content_type() != "application/json":
            self._error(415, "Expected JSON")
            return
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except (ValueError, RecursionError):
            self._error(400, "Invalid JSON")
            return
        if len(body) != length or not isinstance(payload, dict):
            self._error(400, "Expected a complete JSON object")
            return
        model = payload.get("model")
        if not isinstance(model, str) or model not in MODELS:
            self._error(403, "Model unavailable")
            return
        # Forward the parsed object so duplicate keys cannot produce different policies.
        try:
            body = json.dumps(payload, allow_nan=False).encode()
        except (ValueError, RecursionError):
            self._error(400, "Invalid JSON values")
            return
        self._forward(body, model)

    @contextmanager
    def _watch_disconnect(self, upstream_socket, cancelled):
        # A read blocked on upstream headers or a quiet SSE body cannot see a
        # downstream close. Shutdown wakes that read and cancels the native call.
        stop_reader, stop_writer = socket.socketpair()
        with stop_reader, stop_writer, DefaultSelector() as ready:
            ready.register(self.connection, EVENT_READ)
            ready.register(stop_reader, EVENT_READ)

            def watch():
                readers = {key.fileobj for key, _ in ready.select()}
                if stop_reader in readers:
                    return
                try:
                    if self.connection.recv(1, socket.MSG_PEEK):
                        return
                except OSError:
                    pass
                cancelled.set()
                with suppress(OSError):
                    upstream_socket.shutdown(socket.SHUT_RDWR)

            watcher = Thread(target=watch, daemon=True)
            watcher.start()
            try:
                yield
            finally:
                stop_writer.close()
                watcher.join()

    def _forward(self, body=None, model=None):
        conn = HTTPConnection(*self.upstream, timeout=UPSTREAM_IO_TIMEOUT)
        headers = {
            "Authorization": self.authorization.decode(),
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "identity",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        started_reply = False
        started = monotonic()
        headers_ms = first_chunk_ms = upstream_status = None
        outcome = "complete"
        cancelled = Event()
        with ExitStack() as resources:
            resources.callback(conn.close)
            try:
                conn.connect()
                if body is not None:
                    resources.enter_context(self._watch_disconnect(conn.sock, cancelled))
                conn.request(self.command, self.path, body=body, headers=headers)
                print(f"forwarded {self.command} {self.path}", flush=True)
                reply = resources.enter_context(conn.getresponse())
                headers_ms = round((monotonic() - started) * 1000)
                upstream_status = reply.status
                if reply.status >= 400:
                    outcome = "upstream_http_error"
                content_type = reply.headers.get("Content-Type", "application/json")
                retry_after = reply.headers.get("Retry-After")
                if 300 <= reply.status < 400:
                    outcome = "redirect_rejected"
                    self._error(500, "Unexpected upstream redirect")
                    return
                if reply.status in ROUTER_RETRY_CODES:
                    outcome = "retryable_status_mapped"
                    # Stock 9Router replays generation on these statuses. Report the
                    # original status in the error while avoiding a second native call.
                    self._error(500, f"AIStudio2API returned HTTP {reply.status}", retry_after)
                    return
                if reply.status == 200 and reply.headers.get_content_type() == "text/event-stream":
                    started_reply = True
                    self._headers(reply.status, content_type)
                    for chunk in iter(lambda: reply.read1(65536), b""):
                        if first_chunk_ms is None:
                            first_chunk_ms = round((monotonic() - started) * 1000)
                        self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                        self.wfile.flush()
                    if cancelled.is_set():
                        outcome = "downstream_cancelled"
                        return
                    if reply.length not in (None, 0):
                        raise IncompleteRead(b"", reply.length)
                    self.wfile.write(b"0\r\n\r\n")
                    return

                data = reply.read(MAX_REPLY + 1)
                if len(data) > MAX_REPLY:
                    outcome = "oversized_reply"
                    self._error(500, "Upstream response exceeded limit")
                    return
                if reply.status == 200 and self.path == "/v1/models":
                    catalog = json.loads(data)
                    approved = {
                        entry["id"]: entry for entry in catalog["data"] if entry["id"] in MODELS
                    }
                    data = json.dumps({
                        "object": "list",
                        "data": [approved[model_id] for model_id in sorted(approved)],
                    }).encode()
                started_reply = True
                self._headers(reply.status, content_type, length=len(data), retry_after=retry_after)
                self.wfile.write(data)
            except (OSError, HTTPException, ValueError, TypeError, KeyError) as error:
                outcome = "transport_failed"
                if cancelled.is_set():
                    outcome = "downstream_cancelled"
                elif isinstance(error, (TimeoutError, socket.timeout)):
                    outcome = "upstream_timeout"
                if not started_reply and not cancelled.is_set():
                    with suppress(OSError):
                        self._error(500, "Upstream transport failed")
                # An interrupted SSE response ends without a terminating chunk.
                self.close_connection = True
            finally:
                if model is not None:
                    print("transport " + json.dumps({
                        "route": self.path, "model": model, "native_status": upstream_status,
                        "headers_ms": headers_ms, "first_chunk_ms": first_chunk_ms,
                        "elapsed_ms": round((monotonic() - started) * 1000),
                        "outcome": outcome,
                    }, separators=(",", ":")), flush=True)



def make_server(bind, upstream, credential):
    if not credential or any(char.isspace() for char in credential):
        raise ValueError("Expected one non-empty upstream bearer credential")
    return ThreadingHTTPServer(bind, partial(Bridge, upstream=upstream, credential=credential))


if __name__ == "__main__":
    credential_path = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "upstream-key"
    with make_server(("127.0.0.1", 20231), ("127.0.0.1", 2048), credential_path.read_text().strip()) as server:
        server.serve_forever()
