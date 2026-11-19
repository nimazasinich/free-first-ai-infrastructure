#!/usr/bin/env python3
"""Read-only live acceptance. Real generation is optional and bounded."""
import argparse
import json
from pathlib import Path
import subprocess

from probe import MODEL, local_state, request, stream


BRIDGE = "http://127.0.0.1:20231"
GATEWAY = "http://127.0.0.1:20228"
UPSTREAM = "http://127.0.0.1:2048"
CHAT = "/v1/chat/completions"
RESPONSES = "/v1/responses"
ALIAS = "free/" + MODEL


def log(**row):
    print(json.dumps(row), flush=True)


def status(base, path, key=None, body=None, method=None):
    with request(base, path, key, body, method) as response:
        return response.status


def body_for(model, path):
    if path == RESPONSES:
        return {"model": model, "input": "Reply OK."}
    return {"model": model, "messages": [{"role": "user", "content": "Reply OK."}]}


def journal(*args):
    return subprocess.check_output(
        ["journalctl", "-q", "-u", "9router-clean-bridge.service", "-o", "cat", *args],
        text=True,
    )


def policy(public, upstream_key, canary):
    cursor_line = journal("-n", "1", "--show-cursor").splitlines()[-1]
    cursor = cursor_line.removeprefix("-- cursor: ")
    if not cursor or cursor == cursor_line:
        raise RuntimeError("Bridge journal cursor unavailable")
    passed = True
    for label, base in (("public", public), ("router", GATEWAY)):
        for path in (CHAT, RESPONSES):
            for key, model, expected in (
                (None, ALIAS, 401),
                ("invalid-canary-key", ALIAS, 401),
                (canary, "free/gemini-3.1-pro-preview", 403),
                (canary, "mmf/mimo-auto", 403),
                (canary, "oc/unauthorized", 403),
                (canary, "free/not-an-approved-model", 403),
            ):
                actual = status(base, path, key, body_for(model, path))
                log(check="deny", layer=label, path=path, model=model, expected=expected, status=actual)
                passed &= actual == expected
        for key in (None, "invalid-canary-key"):
            actual = status(base, "/v1/models", key)
            log(check="catalog_auth", layer=label, expected=401, status=actual)
            passed &= actual == 401
    for path, method, expected in (
        ("/api/settings", "GET", 404), ("/v1/embeddings", "POST", 404),
        (CHAT, "GET", 405), (RESPONSES, "DELETE", 405),
    ):
        actual = status(public, path, canary, method=method)
        log(check="route", path=path, method=method, expected=expected, status=actual)
        passed &= actual == expected
    for path, model, key, expected in (
        (CHAT, MODEL, None, 401),
        (CHAT, MODEL, "invalid-upstream-key", 401),
        (CHAT, "gemini-3.1-pro-preview", upstream_key, 403),
        (RESPONSES, "unexpected/" + MODEL, upstream_key, 403),
        ("/v1/embeddings", MODEL, upstream_key, 404),
    ):
        actual = status(BRIDGE, path, key, body_for(model, path))
        log(check="bridge_deny", path=path, expected=expected, status=actual)
        passed &= actual == expected
    forwards = sum(line.startswith("forwarded ") for line in journal(f"--after-cursor={cursor}").splitlines())
    log(check="rejected_upstream_forwards", count=forwards)
    passed &= forwards == 0

    for label, base, key, expected in (
        ("direct", UPSTREAM, upstream_key, MODEL),
        ("bridge", BRIDGE, upstream_key, MODEL),
        ("router", GATEWAY, canary, ALIAS),
        ("public", public, canary, ALIAS),
    ):
        with request(base, "/v1/models", key) as reply:
            models = [entry["id"] for entry in json.load(reply).get("data", [])]
            valid = expected in models if label == "direct" else models == [expected]
            log(check="catalog", layer=label, status=reply.status, count=len(models), expected_present=valid)
            passed &= reply.status == 200 and valid
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
    parser.add_argument("suite", choices=("policy", "real", "tools", "restart"))
    args = parser.parse_args()
    upstream_key, canary = local_state(args.root)
    if args.suite == "policy":
        return policy(args.public_url, upstream_key, canary)
    passed = True
    for label, base, key, model in (
        ("direct", UPSTREAM, upstream_key, MODEL),
        ("public", args.public_url, canary, ALIAS),
    ):
        if args.suite == "restart" and label == "direct":
            continue
        if args.suite in ("real", "restart"):
            for responses in (False, True):
                result = stream(base, key, model, responses, max_tokens=1024)
                log(check="live_stream", layer=label, protocol="responses" if responses else "chat", **result)
                passed &= result["complete"] and result["content_events"] > 0
        if args.suite in ("real", "tools"):
            passed &= tools(base, key, model, label)
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
