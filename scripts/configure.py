#!/usr/bin/env python3
"""Apply the single-model policy using 9Router's authenticated management API."""
import argparse
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request

from probe import MODEL, NoRedirect, local_state


def configure(root):
    upstream_key, canary_key = local_state(root)
    env = dict(line.split("=", 1) for line in (root / "env").read_text().splitlines() if "=" in line)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(CookieJar()), NoRedirect(),
    )

    def admin(path, method="GET", body=None):
        req = urllib.request.Request(
            "http://127.0.0.1:20228" + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with opener.open(req, timeout=10) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"{method} {path} returned HTTP {error.code}") from None

    if not admin("/api/auth/login", "POST", {"password": env["INITIAL_PASSWORD"]}).get("success"):
        raise RuntimeError("Local dashboard login failed")
    keys = admin("/api/keys")["keys"]
    if len(keys) != 1 or keys[0]["key"] != canary_key or not keys[0]["isActive"]:
        raise RuntimeError("Gateway API key inventory differs from expected single active canary")
    access = {"restricted": True, "allow": ["free/" + MODEL]}
    key_id = keys[0]["id"]
    if admin(f"/api/keys/{key_id}", "PUT", {"access": access})["key"]["access"] != access:
        raise RuntimeError("9Router did not persist the requested key policy")
    print("9Router canary key restricted to one approved target")

    models = admin("/api/models/custom")["models"]
    if not any(model["id"] == MODEL and model["providerAlias"] == "free" for model in models):
        if not admin("/api/models/custom", "POST", {
            "id": MODEL, "providerAlias": "free", "type": "llm",
        }).get("success"):
            raise RuntimeError("Failed to register the approved model")
    print("Approved model registered in the local catalog")

    # Keep the existing upstream key on the VPS. Write it atomically for systemd LoadCredential.
    if any(char.isspace() for char in upstream_key) or not upstream_key:
        raise RuntimeError("Unexpected upstream credential format")
    with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False) as credential:
        credential.write(upstream_key)
        temporary = credential.name
    os.replace(temporary, root / "upstream.key")
    print("Private bridge credential provisioned locally")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/opt/9router-clean"))
    configure(parser.parse_args().root)
