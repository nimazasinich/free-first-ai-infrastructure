#!/usr/bin/env python3
"""Apply the Free-First model policy using 9Router's authenticated management API."""
import argparse
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request

from probe import MODEL, PILOT_MODEL, NoRedirect, local_state


ACCESS = {"restricted": True, "allow": ["free/" + MODEL]}
PILOT_ACCESS = {"restricted": True, "allow": ["free/" + PILOT_MODEL]}
ALLOWED_ACCESS = (ACCESS, PILOT_ACCESS)
PRODUCTION_KEY_NAMES = {
    "canary",
    "free-first-windows-codex",
    "free-first-windows-cursor",
}
PILOT_KEY_NAME = "free-first-pilot-lite"
APPROVED_MODELS = (
    {"id": MODEL, "providerAlias": "free", "type": "llm"},
    {"id": PILOT_MODEL, "providerAlias": "free", "type": "llm"},
)


def dashboard(root):
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
    return admin


def _ensure_model(admin, model):
    models = admin("/api/models/custom")["models"]
    if any(
        entry["id"] == model["id"] and entry["providerAlias"] == model["providerAlias"]
        for entry in models
    ):
        return
    if not admin("/api/models/custom", "POST", model).get("success"):
        raise RuntimeError(f"Failed to register {model['providerAlias']}/{model['id']}")


def _ensure_key(admin, name, access, keys):
    matches = [key for key in keys if key["name"] == name]
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate key name: {name}")
    if matches and not matches[0]["isActive"]:
        raise RuntimeError(f"Inactive key present: {name}")
    if matches:
        key = matches[0]
        if key["access"] != access:
            key = admin(f"/api/keys/{key['id']}", "PUT", {"access": access})["key"]
            if key["access"] != access:
                raise RuntimeError(f"Failed to persist access for {name}")
        return key
    key = admin("/api/keys", "POST", {"name": name})
    endpoint = "/api/keys/" + key["id"]
    try:
        result = admin(endpoint, "PUT", {"access": access})["key"]
        if result["access"] != access or not result["isActive"]:
            raise RuntimeError(f"New key policy did not persist for {name}")
        return result
    except Exception:
        admin(endpoint, "DELETE")
        raise


def configure(root):
    upstream_key, canary_key = local_state(root)
    admin = dashboard(root)
    keys = admin("/api/keys")["keys"]
    canaries = [key for key in keys if key["isActive"] and key["key"] == canary_key]
    if len(canaries) != 1:
        raise RuntimeError("Expected one active canary key")
    if canaries[0]["name"] != "canary":
        raise RuntimeError("Canary key name mismatch")

    for name in sorted(PRODUCTION_KEY_NAMES):
        matches = [key for key in keys if key["name"] == name and key["isActive"]]
        if name == "canary":
            matches = canaries
        if not matches and name != "canary":
            continue
        if len(matches) != 1:
            raise RuntimeError(f"Expected one active production key named {name}")
        key = matches[0]
        if key["access"] != ACCESS:
            key = admin(f"/api/keys/{key['id']}", "PUT", {"access": ACCESS})["key"]
            if key["access"] != ACCESS:
                raise RuntimeError(f"Production key {name} did not stay flash-only")

    pilot = _ensure_key(admin, PILOT_KEY_NAME, PILOT_ACCESS, keys)
    keys = admin("/api/keys")["keys"]
    for key in keys:
        if not key["isActive"]:
            continue
        if key["access"] not in ALLOWED_ACCESS:
            raise RuntimeError(f"Active key {key['name']} has unexpected model access")
        if key["name"] in PRODUCTION_KEY_NAMES and key["access"] != ACCESS:
            raise RuntimeError(f"Production key {key['name']} is not flash-only")
        if key["name"] == PILOT_KEY_NAME and key["access"] != PILOT_ACCESS:
            raise RuntimeError("Pilot key is not lite-only")
        if key["name"] not in PRODUCTION_KEY_NAMES and key["name"] != PILOT_KEY_NAME:
            raise RuntimeError(f"Unexpected active key name: {key['name']}")

    for model in APPROVED_MODELS:
        _ensure_model(admin, model)
    print("Approved production and pilot models registered")

    output = root / "client-keys"
    output.mkdir(mode=0o700, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=output, delete=False) as data:
        data.write(pilot["key"] + "\n")
    os.replace(data.name, output / "pilot-lite.key")
    print("Pilot key restricted to free/" + PILOT_MODEL)

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
