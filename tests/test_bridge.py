import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

from bridge.bridge import MODEL, make_server


class MockUpstream(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.server.calls.append((self.command, self.path))
        catalog = json.dumps({"data": [{"id": MODEL}, {"id": "other"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(catalog)

    def do_POST(self):
        self.server.calls.append((self.command, self.path))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
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
            self.assertEqual(json.load(reply)["data"], [{"id": MODEL}])

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

    def test_redirect_fails_closed(self):
        with self.call("/v1/responses", {"model": MODEL, "mock_status": 302}) as reply:
            self.assertEqual(reply.status, 500)
        self.assertEqual(len(self.mock.calls), 1)


if __name__ == "__main__":
    unittest.main()
