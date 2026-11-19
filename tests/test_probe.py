from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts.probe import stream


class StreamProbeTests(TestCase):
    def probe(self, events, *, responses=False):
        reply = BytesIO(b"".join(b"data: " + event + b"\n\n" for event in events))
        reply.status = 200
        reply.headers = Mock()
        reply.headers.get_content_type.return_value = "text/event-stream"
        with patch("scripts.probe.request", return_value=reply):
            return stream("http://fixture", "key", "fixture-model", responses=responses)

    def test_responses_done_requires_success_event(self):
        events = [b'{"type":"response.output_text.delta","delta":"partial"}', b"[DONE]"]
        self.assertFalse(self.probe(events, responses=True)["complete"])

    def test_responses_explicit_failure_is_terminal(self):
        for event_type in ("response.failed", "response.incomplete", "error"):
            with self.subTest(event_type=event_type):
                failed = ('{"type":"' + event_type + '"}').encode()
                events = [b'{"type":"response.output_text.delta","delta":"partial"}', failed, b"[DONE]"]
                result = self.probe(events, responses=True)
                self.assertFalse(result["complete"])
                self.assertEqual(result["finish"], event_type)

    def test_responses_reports_success_and_actual_model(self):
        result = self.probe([
            b'{"type":"response.output_text.delta","delta":"ok"}',
            b'{"type":"response.completed","response":{"model":"fixture-model"}}',
            b"[DONE]",
        ], responses=True)
        self.assertTrue(result["complete"])
        self.assertEqual(result["response_models"], ["fixture-model"])

    def test_chat_error_cannot_be_hidden_by_done(self):
        result = self.probe([
            b'{"model":"fixture-model","choices":[{"delta":{"content":"partial"}}]}',
            b'{"error":{"type":"stream_error"}}',
            b"[DONE]",
        ])
        self.assertFalse(result["complete"])
        self.assertEqual(result["content_events"], 1)

    def test_chat_reports_normal_finish_with_done(self):
        result = self.probe([
            b'{"model":"fixture-model","choices":[{"delta":{"content":"ok"}}]}',
            b'{"choices":[{"finish_reason":"stop"}]}',
            b"[DONE]",
        ])
        self.assertTrue(result["complete"])
        self.assertEqual(result["response_models"], ["fixture-model"])
