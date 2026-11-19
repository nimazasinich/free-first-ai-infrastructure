from io import BytesIO
import json
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts.check_client import gateway_origin, verify


class ClientCheckTests(TestCase):
    def reply(self, status, body=b""):
        response = BytesIO(body)
        response.status = status
        response.headers = Mock()
        response.headers.get_content_type.return_value = "application/json"
        return response

    def run_checks(self, ids, authorized_status=200):
        model = "free/gemini-3.8-flash"
        origin = "https://gateway.example"
        responses = [
            self.reply(authorized_status, json.dumps({"data": [{"id": name} for name in ids]}).encode()),
            *(self.reply(status) for status in (401, 401, 405, 405, 404)),
        ]
        with patch("scripts.check_client.request", side_effect=responses) as request:
            evidence = list(verify(origin, "fixture-key", model))
        self.assertTrue(all(call.kwargs == {"method": "GET", "timeout": 8} for call in request.call_args_list))
        self.assertTrue(all(call.args[0] == origin for call in request.call_args_list))
        self.assertEqual([call.args[2] for call in request.call_args_list].count("fixture-key"), 1)
        self.assertNotIn("fixture-key", repr(evidence))
        return evidence

    def test_scope_and_errors_pass(self):
        evidence = self.run_checks(["free/gemini-3.8-flash"])
        self.assertTrue(all(row["result"] == "PASS" for row in evidence))

    def test_extra_model_or_redirect_fails(self):
        for ids, status in (
            (["free/gemini-3.8-flash", "free/gemini-3.5-flash-lite"], 200),
            (["free/gemini-3.8-flash"], 302),
        ):
            with self.subTest(status=status, ids=ids):
                self.assertEqual(self.run_checks(ids, status)[0]["result"], "FAIL")

    def test_gateway_origin_requires_a_bare_https_v1_url(self):
        self.assertEqual(gateway_origin("https://gateway.example/v1/"), "https://gateway.example")
        for url in (
            "http://gateway.example/v1",
            "https://user@gateway.example/v1",
            "https://gateway.example:123/v1",
            "https://gateway.example/v1/chat/completions",
            "https://gateway.example/v1?key=fixture",
            "https://gateway.example/v1#",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                gateway_origin(url)
