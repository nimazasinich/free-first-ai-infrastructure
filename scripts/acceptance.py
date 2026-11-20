#!/usr/bin/env python3
"""Read-only live acceptance. Real generation is optional and bounded."""
import argparse
from contextlib import closing
from http.client import HTTPException
import json
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from probe import MODEL, MODELS, PILOT_31_MODEL, PILOT_MODEL, local_state, request, stream


BRIDGE = "http://127.0.0.1:20231"
GATEWAY = "http://127.0.0.1:20228"
UPSTREAM = "http://127.0.0.1:2048"
PROTOCOL = "http://127.0.0.1:20232"
FALLBACK = "gemini-lite-safe-fallback"
CHAT = "/v1/chat/completions"
RESPONSES = "/v1/responses"
ALIAS = "free/" + MODEL
PILOT_ALIAS = "free/" + PILOT_MODEL
PILOT_31_ALIAS = "free/" + PILOT_31_MODEL
BRIDGE_CATALOG = sorted(MODELS)


def log(**row):
    print(json.dumps(row), flush=True)


def status(base, path, key=None, body=None, method=None):
    with request(base, path, key, body, method) as response:
        return response.status


def body_for(model, path):
    if path == RESPONSES:
        return {"model": model, "input": "Reply OK."}
    return {"model": model, "messages": [{"role": "user", "content": "Reply OK."}]}


def journal(*args, unit="9router-clean-bridge"):
    unit += ".service"
    return subprocess.check_output(
        ["journalctl", "-q", "-u", unit, "-o", "cat", *args],
        text=True,
    )


def load_models(base, key, attempts=4):
    delay = 2
    for attempt in range(attempts):
        with request(base, "/v1/models", key) as reply:
            if reply.status == 429 and attempt + 1 < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 15)
                continue
            if reply.status != 200:
                return reply.status, []
            payload = reply.read()
            try:
                models = [entry["id"] for entry in json.loads(payload).get("data", [])]
            except (ValueError, TypeError, AttributeError):
                return reply.status, []
            return reply.status, models
    return 429, []


def stored_key_policy(root):
    expected = {
        "canary": [ALIAS],
        "free-first-windows-cursor": [ALIAS],
        "free-first-windows-codex": [ALIAS],
        "free-first-pilot-lite": [PILOT_ALIAS],
        "free-first-pilot-31-lite": [PILOT_31_ALIAS],
        "free-first-pilot-lite-fallback": ["free/gemini-lite-safe-fallback"],
    }
    with closing(sqlite3.connect(f"file:{root / 'data/db/data.sqlite'}?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT name, accessRestricted, accessAllow FROM apiKeys WHERE isActive = 1").fetchall()
    actual = {name: json.loads(allow or "[]") for name, restricted, allow in rows if restricted == 1}
    passed = len(rows) == len(expected) and actual == expected
    log(check="stored_key_policy", active=len(rows), restricted=len(actual), matches=passed)
    return passed


def check_rejected_upstream_forwards(started):
    passed = True
    for unit in ("9router-clean-bridge", "9router-clean-protocol"):
        forwards = sum(line.startswith("forwarded ") for line in journal(
            f"--since={started}", unit=unit,
        ).splitlines())
        log(check="rejected_upstream_forwards", unit=unit, count=forwards)
        passed &= forwards == 0
    return passed


def policy(public, upstream_key, canary, pilot_key=None, pilot_31_key=None, windows_keys=(), *, fallback_key):
    # A quiet unit may have no retained entries and therefore no journal cursor.
    started = f"@{time.time():.6f}"
    passed = True
    # Full negative matrix on the local router. Keep the public edge sample small so
    # Edge Guard rate limits do not turn an expanded deny suite into false failures.
    deny_cases = (
        (None, ALIAS, 401),
        ("invalid-canary-key", ALIAS, 401),
        (canary, "free/gemini-3.1-pro-preview", 403),
        (canary, "mmf/mimo-auto", 403),
        (canary, "oc/unauthorized", 403),
        (canary, "free/not-an-approved-model", 403),
        (canary, PILOT_ALIAS, 403),
        (canary, PILOT_31_ALIAS, 403),
    )
    for path in (CHAT, RESPONSES):
        for key, model, expected in deny_cases:
            actual = status(GATEWAY, path, key, body_for(model, path))
            log(check="deny", layer="router", path=path, model=model, expected=expected, status=actual)
            passed &= actual == expected
        if pilot_key:
            for model, expected in (
                (ALIAS, 403),
                (PILOT_31_ALIAS, 403),
                ("free/gemini-3.1-pro-preview", 403),
                ("free/not-an-approved-model", 403),
            ):
                actual = status(GATEWAY, path, pilot_key, body_for(model, path))
                log(
                    check="pilot_deny", layer="router", path=path, model=model,
                    expected=expected, status=actual,
                )
                passed &= actual == expected
        if pilot_31_key:
            for model, expected in (
                (ALIAS, 403),
                (PILOT_ALIAS, 403),
                ("free/gemini-3.1-pro-preview", 403),
                ("free/not-an-approved-model", 403),
            ):
                actual = status(GATEWAY, path, pilot_31_key, body_for(model, path))
                log(
                    check="pilot31_deny", layer="router", path=path, model=model,
                    expected=expected, status=actual,
                )
                passed &= actual == expected
    for label, key in windows_keys:
        for path in (CHAT, RESPONSES):
            for model in (PILOT_ALIAS, PILOT_31_ALIAS):
                actual = status(GATEWAY, path, key, body_for(model, path))
                log(
                    check="windows_key_deny", client=label, path=path, model=model,
                    expected=403, status=actual,
                )
                passed &= actual == 403
    for key in (None, "invalid-canary-key"):
        actual = status(GATEWAY, "/v1/models", key)
        log(check="catalog_auth", layer="router", expected=401, status=actual)
        passed &= actual == 401

    public_cases = (
        (None, ALIAS, 401),
        ("invalid-canary-key", ALIAS, 401),
        (canary, "free/gemini-3.1-pro-preview", 403),
        (canary, PILOT_ALIAS, 403),
        (canary, PILOT_31_ALIAS, 403),
    )
    for key, model, expected in public_cases:
        actual = status(public, CHAT, key, body_for(model, CHAT))
        log(check="deny", layer="public", path=CHAT, model=model, expected=expected, status=actual)
        passed &= actual == expected
    if pilot_key:
        actual = status(public, CHAT, pilot_key, body_for(ALIAS, CHAT))
        log(check="pilot_deny", layer="public", path=CHAT, model=ALIAS, expected=403, status=actual)
        passed &= actual == 403
    if pilot_31_key:
        actual = status(public, CHAT, pilot_31_key, body_for(ALIAS, CHAT))
        log(check="pilot31_deny", layer="public", path=CHAT, model=ALIAS, expected=403, status=actual)
        passed &= actual == 403
    for key in (None, "invalid-canary-key"):
        actual = status(public, "/v1/models", key)
        # Edge Guard may answer 429 under burst; that still denies an unauthenticated catalog.
        ok = actual in (401, 429)
        log(check="catalog_auth", layer="public", expected="401|429", status=actual, ok=ok)
        passed &= ok

    for path, method, expected in (
        ("/api/settings", "GET", 404), ("/v1/embeddings", "POST", 404),
        (CHAT, "GET", 405), (RESPONSES, "DELETE", 405),
    ):
        actual = status(public, path, canary, method=method)
        log(check="route", path=path, method=method, expected=expected, status=actual)
        passed &= actual == expected
    message = {"model": MODEL, "max_tokens": 8, "messages": [{"role": "user", "content": "x"}]}
    for path, payload in (
        ("/v1/messages", message),
        ("/v1/messages/count_tokens", message),
        (f"/v1beta/models/{MODEL}:generateContent", {}),
        (f"/v1beta/models/{MODEL}:countTokens", {}),
        (f"/v1beta/models/{MODEL}:streamGenerateContent?alt=sse", {}),
    ):
        actual = status(public, path, canary, payload)
        log(check="protocol_public_closed", path=path, expected=404, status=actual)
        passed &= actual == 404
    for path, key, expected in (
        ("/v1beta/models", None, 403),
        ("/v1beta/models", "invalid-discovery-key", 403),
        ("/v1beta/models", pilot_key, 403),
        (f"/v1beta/models/{PILOT_MODEL}", canary, 404),
        ("/v1beta/interactions", canary, 404),
    ):
        actual = status(public, path, key)
        log(check="public_discovery_deny", path=path, expected=expected, status=actual)
        passed &= actual == expected
    for path, list_reply in (("/v1beta/models", True), (f"/v1beta/models/{MODEL}", False)):
        try:
            catalog_request = Request(public + path, headers={"x-goog-api-key": canary})
            with urlopen(catalog_request, timeout=10) as reply:
                data = json.load(reply)
            models = data["models"] if list_reply else [data]
            valid = (
                [entry["name"] for entry in models] == [f"models/{MODEL}"]
                and not models[0]["supportedGenerationMethods"]
            )
        except (HTTPError, ValueError, KeyError):
            valid = False
        log(check="public_gemini_discovery", path=path, matches=valid)
        passed &= valid
    for path, key, payload, expected in (
        ("/v1/messages", None, message, 401),
        ("/v1/messages/count_tokens", None, message, 401),
        ("/v1/messages", pilot_key, message, 401),
        ("/v1/messages", canary, dict(message, model=PILOT_MODEL), 404),
        ("/v1beta/models", None, None, 403),
        (f"/v1beta/models/{PILOT_MODEL}:generateContent", canary, {}, 404),
        (f"/v1beta/models/{MODEL}:embedContent", canary, {}, 404),
    ):
        actual = status(PROTOCOL, path, key, payload)
        log(check="protocol_loopback_deny", path=path, expected=expected, status=actual)
        passed &= actual == expected
    try:
        catalog_request = Request(PROTOCOL + "/v1beta/models", headers={"x-goog-api-key": canary})
        with urlopen(catalog_request, timeout=10) as reply:
            allowed = [entry["name"] for entry in json.load(reply)["models"]]
    except (HTTPError, ValueError, KeyError):
        allowed = []
    catalog_ok = allowed == [f"models/{MODEL}"]
    log(check="protocol_loopback_gemini_catalog", matches=catalog_ok)
    passed &= catalog_ok
    for path, model, key, expected in (
        (CHAT, MODEL, None, 401),
        (CHAT, MODEL, "invalid-upstream-key", 401),
        (CHAT, "gemini-3.1-pro-preview", upstream_key, 403),
        (CHAT, FALLBACK, upstream_key, 422),
        (RESPONSES, FALLBACK, upstream_key, 422),
        (RESPONSES, "unexpected/" + MODEL, upstream_key, 403),
        ("/v1/embeddings", MODEL, upstream_key, 404),
        ("/v1/messages", MODEL, upstream_key, 404),
    ):
        actual = status(BRIDGE, path, key, body_for(model, path) if path != "/v1/embeddings" else body_for(model, CHAT))
        log(check="bridge_deny", path=path, expected=expected, status=actual)
        passed &= actual == expected
    for label, base in (("router", GATEWAY), ("public", public)):
        for path in (CHAT, RESPONSES):
            # A model-only body is deliberately non-generating if the gate ever regresses.
            actual = status(base, path, fallback_key, {"model": f"free/{FALLBACK}"})
            log(check="fallback_generation_closed", layer=label, path=path, expected=422, status=actual)
            passed &= actual == 422
    passed &= check_rejected_upstream_forwards(started)

    time.sleep(3)
    for label, base, key, expected in (
        ("direct", UPSTREAM, upstream_key, MODEL),
        ("bridge", BRIDGE, upstream_key, BRIDGE_CATALOG),
        ("router", GATEWAY, canary, [ALIAS]),
        ("public", public, canary, [ALIAS]),
    ):
        code, models = load_models(base, key)
        if label == "direct":
            valid = expected in models
        else:
            valid = models == expected
        log(check="catalog", layer=label, status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
    if pilot_key:
        code, models = load_models(public, pilot_key)
        valid = models == [PILOT_ALIAS]
        log(check="catalog", layer="public_pilot", status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
        code, models = load_models(GATEWAY, pilot_key)
        valid = models == [PILOT_ALIAS]
        log(check="catalog", layer="router_pilot", status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
    if pilot_31_key:
        code, models = load_models(public, pilot_31_key)
        valid = models == [PILOT_31_ALIAS]
        log(check="catalog", layer="public_pilot31", status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
        code, models = load_models(GATEWAY, pilot_31_key)
        valid = models == [PILOT_31_ALIAS]
        log(check="catalog", layer="router_pilot31", status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
    for label, base in (("router", GATEWAY), ("public", public)):
        code, models = load_models(base, fallback_key)
        valid = code == 200 and models == [f"free/{FALLBACK}"]
        log(check="fallback_key_catalog", layer=label, status=code, matches=valid)
        passed &= valid
    for label, key in windows_keys:
        code, models = load_models(GATEWAY, key)
        valid = models == [ALIAS]
        log(check="windows_key_catalog", client=label, status=code, count=len(models), expected_present=valid)
        passed &= code == 200 and valid
    return passed


def streamed_tool(reply):
    finish = None
    finished = False
    calls = {}
    for line in reply:
        if not line.startswith(b"data:"):
            continue
        fragment = line[5:].strip()
        if fragment == b"[DONE]":
            finished = True
            continue
        if not fragment:
            continue
        choice = (json.loads(fragment).get("choices") or [{}])[0]
        finish = choice.get("finish_reason") or finish
        for delta in choice.get("delta", {}).get("tool_calls", []):
            index = delta.get("index", 0)
            call = calls.setdefault(index, {"function": {"name": "", "arguments": ""}})
            for field in ("id", "type"):
                if delta.get(field):
                    call[field] = delta[field]
            for field in ("name", "arguments"):
                if delta.get("function", {}).get(field):
                    call["function"][field] += delta["function"][field]
    assistant = {"role": "assistant", "content": None, "tool_calls": list(calls.values())}
    return (finish if finished else None), assistant


def tools(base, key, model, label):
    messages = [{"role": "user", "content": "Call lookup_color with item sky, then report the returned color."}]
    tool = {
        "type": "function",
        "function": {
            "name": "lookup_color",
            "description": "Return the color of the named item.",
            "parameters": {
                "type": "object", "properties": {"item": {"type": "string"}}, "required": ["item"],
            },
        },
    }
    body = {
        "model": model, "messages": messages, "tools": [tool],
        "tool_choice": {"type": "function", "function": {"name": "lookup_color"}},
        "max_tokens": 1024, "temperature": 0.0, "stream": True,
    }
    with request(base, CHAT, key, body) as reply:
        if reply.status != 200 or reply.headers.get_content_type() != "text/event-stream":
            log(check="structured_tool_sse", layer=label, status=reply.status, valid=False)
            return False
        finish, assistant = streamed_tool(reply)
        calls = assistant.get("tool_calls") or []
        first = calls[0] if len(calls) == 1 else {}
        function = first.get("function") or {}
        arguments = json.loads(function.get("arguments") or "{}")
        valid = (
            finish == "tool_calls"
            and first.get("type") == "function" and bool(first.get("id"))
            and function.get("name") == "lookup_color" and arguments.get("item") == "sky"
        )
        log(check="structured_tool_sse", layer=label, status=reply.status, finish=finish, valid=valid)
    if not valid:
        return False
    body["messages"] = messages + [assistant, {
        "role": "tool", "tool_call_id": first["id"], "content": '{"color":"cerulean"}',
    }]
    body["tool_choice"] = "none"
    body["stream"] = False
    with request(base, CHAT, key, body) as reply:
        if reply.headers.get_content_type() != "application/json":
            log(check="tool_result_continuation", layer=label, status=reply.status, valid=False)
            return False
        data = json.load(reply)
        choice = (data.get("choices") or [{}])[0]
        answer = choice.get("message", {}).get("content") or ""
        valid = reply.status == 200 and "cerulean" in answer.lower()
        log(check="tool_result_continuation", layer=label, status=reply.status,
            finish=choice.get("finish_reason"), valid=valid)
    return valid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/opt/9router-clean"))
    parser.add_argument("--public-url", required=True)
    parser.add_argument("--layer", choices=("direct", "public", "public_pilot"))
    parser.add_argument("suite", choices=("policy", "real", "tools", "restart", "pilot", "pilot31"))
    args = parser.parse_args()
    upstream_key, canary = local_state(args.root)
    pilot_path = args.root / "client-keys" / "pilot-lite.key"
    pilot_key = pilot_path.read_text().strip() if pilot_path.is_file() else None
    pilot_31_path = args.root / "client-keys" / "pilot-31-lite.key"
    pilot_31_key = pilot_31_path.read_text().strip() if pilot_31_path.is_file() else None
    if args.suite == "policy":
        stored = stored_key_policy(args.root)
        windows_keys = [
            (label, (args.root / "client-keys" / f"{label}.key").read_text().strip())
            for label in ("cursor", "codex")
        ]
        return (
            policy(
                args.public_url, upstream_key, canary, pilot_key, pilot_31_key, windows_keys,
                fallback_key=(args.root / "client-keys" / "pilot-lite-fallback.key").read_text().strip(),
            )
            and stored
        )
    if args.suite in ("pilot", "pilot31"):
        if args.suite == "pilot":
            if not pilot_key:
                log(check="pilot_key", present=False)
                return False
            targets = (
                ("direct", UPSTREAM, upstream_key, PILOT_MODEL),
                ("public_pilot", args.public_url, pilot_key, PILOT_ALIAS),
            )
        else:
            if not pilot_31_key:
                log(check="pilot31_key", present=False)
                return False
            targets = (
                ("direct", UPSTREAM, upstream_key, PILOT_31_MODEL),
                ("public_pilot31", args.public_url, pilot_31_key, PILOT_31_ALIAS),
            )
        passed = True
        for label, base, key, model in targets:
            if args.layer and label != args.layer:
                continue
            for responses in (False, True):
                protocol = "responses" if responses else "chat"
                try:
                    result = stream(base, key, model, responses, max_tokens=256)
                    log(check="live_stream", layer=label, protocol=protocol, model=model, **result)
                    passed &= result["complete"] and result["content_events"] > 0
                except (OSError, HTTPException, ValueError) as error:
                    log(check="live_stream", layer=label, protocol=protocol, failure=type(error).__name__)
                    passed = False
        return passed
    passed = True
    for label, base, key, model in (
        ("direct", UPSTREAM, upstream_key, MODEL),
        ("public", args.public_url, canary, ALIAS),
    ):
        if args.layer and label != args.layer:
            continue
        if args.suite == "restart" and label == "direct":
            continue
        if args.suite in ("real", "restart"):
            for responses in (False, True):
                protocol = "responses" if responses else "chat"
                try:
                    result = stream(base, key, model, responses, max_tokens=1024)
                    log(check="live_stream", layer=label, protocol=protocol, **result)
                    passed &= result["complete"] and result["content_events"] > 0
                except (OSError, HTTPException, ValueError) as error:
                    log(check="live_stream", layer=label, protocol=protocol, failure=type(error).__name__)
                    passed = False
        if args.suite in ("real", "tools"):
            try:
                passed &= tools(base, key, model, label)
            except (OSError, HTTPException, ValueError) as error:
                log(check="tool_round_trip", layer=label, failure=type(error).__name__)
                passed = False
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
