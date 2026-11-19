#!/usr/bin/env python3
"""Check an approved application credential against the public gateway without generation."""
import argparse
from http.client import HTTPException
import json
import os
from urllib.parse import urlsplit

from scripts.probe import request


MAX_CATALOG_BYTES = 64 * 1024
DEFAULT_URL = "https://r9.185-221-237-84.sslip.io/v1"


def gateway_origin(url):
    parts = urlsplit(url)
    if (
        not url.isascii()
        or "\\" in url
        or any(not 33 <= ord(char) <= 126 for char in url)
        or parts.scheme != "https"
        or not parts.hostname
        or parts.port not in (None, 443)
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("/v1", "/v1/")
        or "?" in url
        or "#" in url
    ):
        raise ValueError("Expected an HTTPS gateway URL ending in /v1")
    return f"https://{parts.netloc}"


def verify(origin, key, model):
    checks = (
        ("authorized_catalog", "/v1/models", key, 200),
        ("missing_credential", "/v1/models", None, 401),
        ("invalid_credential", "/v1/models", "invalid-free-first-client-check", 401),
        ("chat_wrong_method", "/v1/chat/completions", None, 405),
        ("responses_wrong_method", "/v1/responses", None, 405),
        ("unsupported_route", "/v1/embeddings", None, 404),
    )
    for label, path, auth, expected in checks:
        evidence = {"check": label, "expected_status": expected}
        passed = False
        try:
            with request(origin, path, auth, method="GET", timeout=8) as response:
                evidence["http_status"] = response.status
                passed = response.status == expected
                if passed and label == "authorized_catalog":
                    body = response.read(MAX_CATALOG_BYTES + 1)
                    passed = False
                    if len(body) <= MAX_CATALOG_BYTES and response.headers.get_content_type() == "application/json":
                        catalog = json.loads(body)
                        passed = (
                            isinstance(catalog, dict)
                            and isinstance(catalog.get("data"), list)
                            and len(catalog["data"]) == 1
                            and isinstance(catalog["data"][0], dict)
                            and catalog["data"][0].get("id") == model
                        )
                    evidence["exact_model_scope"] = passed
        except (OSError, HTTPException, ValueError) as error:
            evidence["error_type"] = type(error).__name__
        yield {**evidence, "result": "PASS" if passed else "FAIL"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", required=True, help="The exact public model alias authorized for this key")
    args = parser.parse_args()
    key = os.environ.get("FREE_FIRST_GATEWAY_KEY", "")
    if not key or not key.isascii() or any(not 33 <= ord(char) <= 126 for char in key):
        parser.error("Set FREE_FIRST_GATEWAY_KEY to the approved application credential")
    try:
        origin = gateway_origin(args.url)
    except ValueError:
        parser.error("Expected an HTTPS gateway URL ending in /v1")
    passed = True
    for evidence in verify(origin, key, args.model):
        print(json.dumps(evidence), flush=True)
        passed &= evidence["result"] == "PASS"
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
