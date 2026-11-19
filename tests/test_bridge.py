import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
import unittest
from unittest.mock import patch

from bridge.bridge import MODEL, MODELS, PILOT_MODEL, make_server


class MockUpstream(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.server.calls.append((self.command, self.path))
        catalog = json.dumps({
            "data": [{"id": MODEL}, {"id": PILOT_MODEL}, {"id": "other"}],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(catalog)

    def do_POST(self):
        self.server.calls.append((self.command, self.path))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body.get("truncate"):
            chunk = b"data: first\n\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(chunk) + 10))
            self.end_headers()
            self.wfile.write(chunk)
            return
        if body.get("reset"):
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        if body.get("disconnect_fixture"):
            if body["disconnect_fixture"] == "during_stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b"data: first\n\n")
                self.wfile.flush()
            self.server.waiting.set()
            self.connection.settimeout(2)
            try:
                if not self.connection.recv(1):
                    self.server.disconnected.set()
            except socket.timeout:
                pass
            return
        if "mock_status" in body:
            self.send_response(body["mock_status"])
            self.send_header("Retry-After", "17")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_fixture","function":{"name":"lookup","arguments":"{"}}]}}]}\n\n')
        self.wfile.flush()
        # Releasing this event after reading the first frame proves incremental delivery.
        if self.server.release.wait(5):
            self.wfile.write(b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"}"}}]}}]}\n\ndata: [DONE]\n\n')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.mock = ThreadingHTTPServer(("127.0.0.1", 0), MockUpstream)
        self.mock.calls = []
        self.mock.release = threading.Event()
        self.mock.waiting = threading.Event()
        self.mock.disconnected = threading.Event()
        self.bridge = make_server(("127.0.0.1", 0), self.mock.server_address, "test-key")
        for server in (self.mock, self.bridge):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

    def call(self, path, body=None, key="test-key", method=None):
        conn = http.client.HTTPConnection(*self.bridge.server_address, timeout=3)
        self.addCleanup(conn.close)
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = "Bearer " + key
        conn.request(method or ("GET" if body is None else "POST"), path,
                     body=None if body is None else json.dumps(body), headers=headers)
        return conn.getresponse()

    def test_forbidden_requests_never_reach_upstream(self):
        for path, model, key, status in (
            ("/v1/chat/completions", "blocked", "test-key", 403),
            ("/v1/responses", "free/" + MODEL, "test-key", 403),
            ("/v1/responses", [], "test-key", 403),
            ("/v1/responses", MODEL, "", 401),
            ("/v1/responses", MODEL, "invalid", 401),
            ("/v1/responses?extra=1", MODEL, "test-key", 404),
            ("/v1/embeddings", MODEL, "test-key", 404),
        ):
            with self.subTest(path=path, model=model, status=status):
                with self.call(path, {"model": model}, key) as reply:
                    self.assertEqual(reply.status, status)
        self.assertEqual(self.mock.calls, [])

    def test_catalog_filters_unapproved_models(self):
        with self.call("/v1/models") as reply:
            self.assertEqual(reply.status, 200)
            self.assertEqual(
                json.load(reply)["data"],
                [{"id": model_id} for model_id in sorted(MODELS)],
            )

    def test_pilot_model_is_forwarded(self):
        with self.call("/v1/chat/completions", {"model": PILOT_MODEL, "stream": True}) as reply:
            self.assertEqual(reply.status, 200)
            self.mock.release.set()
            reply.read()
        self.assertEqual(self.mock.calls, [("POST", "/v1/chat/completions")])

    def test_sse_delivers_tool_delta_before_upstream_finishes(self):
        try:
            with self.call("/v1/chat/completions", {"model": MODEL, "stream": True}) as reply:
                self.assertEqual(reply.status, 200)
                self.assertEqual(reply.headers.get_content_type(), "text/event-stream")
                first = reply.readline()
                self.assertIn(b'"name":"lookup"', first)
                self.mock.release.set()
                rest = reply.read()
                self.assertIn(b'data: [DONE]', rest)
                self.assertIn(b'"arguments":"}"', rest)
        finally:
            self.mock.release.set()
        self.assertEqual(len(self.mock.calls), 1)

    def test_status_retry_after_and_no_retry(self):
        for status in (401, 403, 429):
            with self.subTest(status=status):
                with self.call("/v1/responses", {"model": MODEL, "mock_status": status}) as reply:
                    self.assertEqual(reply.status, status)
                    self.assertEqual(reply.headers["Retry-After"], "17")
        self.assertEqual(len(self.mock.calls), 3)

    def test_retryable_status_becomes_a_single_terminal_error(self):
        for status in (502, 503, 504):
            with self.subTest(status=status):
                with self.call("/v1/responses", {"model": MODEL, "mock_status": status}) as reply:
                    self.assertEqual(reply.status, 500)
                    self.assertEqual(reply.headers["Retry-After"], "17")
                    self.assertIn(str(status), json.load(reply)["error"]["message"])
        self.assertEqual(len(self.mock.calls), 3)

    def test_upstream_silent_headers_time_out_once(self):
        with patch("bridge.bridge.UPSTREAM_IO_TIMEOUT", 0.25):
            with self.call("/v1/responses", {"model": MODEL, "disconnect_fixture": "before_headers"}) as reply:
                self.assertEqual(reply.status, 500)
        self.assertTrue(self.mock.disconnected.wait(1))
        self.assertEqual(len(self.mock.calls), 1)

    def test_truncated_sse_does_not_end_cleanly(self):
        with self.call("/v1/responses", {"model": MODEL, "truncate": True}) as reply:
            self.assertEqual(reply.status, 200)
            self.assertEqual(reply.readline(), b"data: first\n")
            with self.assertRaises(http.client.IncompleteRead):
                reply.read()
        self.assertEqual(len(self.mock.calls), 1)

    def test_upstream_disconnect_before_headers_is_terminal(self):
        with self.call("/v1/responses", {"model": MODEL, "reset": True}) as reply:
            self.assertEqual(reply.status, 500)
            self.assertEqual(json.load(reply)["error"]["message"], "Upstream transport failed")
        self.assertEqual(len(self.mock.calls), 1)

    def test_client_disconnect_closes_silent_upstream(self):
        for phase in ("before_headers", "during_stream"):
            with self.subTest(phase=phase):
                self.mock.waiting.clear()
                self.mock.disconnected.clear()
                body = json.dumps({"model": MODEL, "disconnect_fixture": phase}).encode()
                headers = (
                    "POST /v1/chat/completions HTTP/1.1\r\n"
                    "Host: localhost\r\nAuthorization: Bearer test-key\r\n"
                    f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
                ).encode()
                with socket.create_connection(self.bridge.server_address, timeout=2) as client:
                    client.sendall(headers + body)
                    self.assertTrue(self.mock.waiting.wait(1))
                    if phase == "during_stream":
                        with client.makefile("rb") as reply:
                            for line in reply:
                                if b"data: first" in line:
                                    break
                            else:
                                self.fail("bridge closed before sending the first SSE frame")
                    client.shutdown(socket.SHUT_RDWR)
                self.assertTrue(self.mock.disconnected.wait(1), "upstream socket stayed open")
        self.assertEqual(len(self.mock.calls), 2)

    def test_redirect_fails_closed(self):
        with self.call("/v1/responses", {"model": MODEL, "mock_status": 302}) as reply:
            self.assertEqual(reply.status, 500)
        self.assertEqual(len(self.mock.calls), 1)


if __name__ == "__main__":
    unittest.main()
