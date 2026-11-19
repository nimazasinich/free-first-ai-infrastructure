#!/usr/bin/env python3
"""Private, authenticated AIStudio2API transport for the single approved model."""
from functools import partial
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path


MODEL = "gemini-3.8-flash"
POST_ROUTES = {"/v1/chat/completions", "/v1/responses"}
MAX_BODY = 6 * 1024 * 1024
MAX_REPLY = 16 * 1024 * 1024
ROUTER_RETRY_CODES = {502, 503, 504}


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
        if payload.get("model") != MODEL:
            self._error(403, "Model unavailable")
            return
        # Forward the parsed object so duplicate keys cannot produce different policies.
        try:
            body = json.dumps(payload, allow_nan=False).encode()
        except (ValueError, RecursionError):
            self._error(400, "Invalid JSON values")
            return
        self._forward(body)

    def _forward(self, body=None):
        conn = HTTPConnection(*self.upstream, timeout=115)
        headers = {
            "Authorization": self.authorization.decode(),
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "identity",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        started_reply = False
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            print(f"forwarded {self.command} {self.path}", flush=True)
            reply = conn.getresponse()
            content_type = reply.headers.get("Content-Type", "application/json")
            retry_after = reply.headers.get("Retry-After")
            if 300 <= reply.status < 400:
                self._error(500, "Unexpected upstream redirect")
                return
            if reply.status in ROUTER_RETRY_CODES:
                # Stock 9Router replays generation on these statuses. Report the
                # original status in the error while avoiding a second native call.
                self._error(500, f"AIStudio2API returned HTTP {reply.status}", retry_after)
                return
            if reply.status == 200 and reply.headers.get_content_type() == "text/event-stream":
                started_reply = True
                self._headers(reply.status, content_type)
                for chunk in iter(lambda: reply.read1(65536), b""):
                    self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                return

            data = reply.read(MAX_REPLY + 1)
            if len(data) > MAX_REPLY:
                self._error(500, "Upstream response exceeded limit")
                return
            if reply.status == 200 and self.path == "/v1/models":
                catalog = json.loads(data)
                data = json.dumps({
                    "object": "list",
                    "data": [entry for entry in catalog["data"] if entry["id"] == MODEL],
                }).encode()
            started_reply = True
            self._headers(reply.status, content_type, length=len(data), retry_after=retry_after)
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except (OSError, HTTPException, ValueError, TypeError, KeyError):
            if not started_reply:
                self._error(500, "Upstream transport failed")
            # End a failed active stream without a terminating chunk.
            self.close_connection = True
        finally:
            conn.close()


def make_server(bind, upstream, credential):
    if not credential or any(char.isspace() for char in credential):
        raise ValueError("Expected one non-empty upstream bearer credential")
    return ThreadingHTTPServer(bind, partial(Bridge, upstream=upstream, credential=credential))


if __name__ == "__main__":
    credential_path = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "upstream-key"
    with make_server(("127.0.0.1", 20231), ("127.0.0.1", 2048), credential_path.read_text().strip()) as server:
        server.serve_forever()
