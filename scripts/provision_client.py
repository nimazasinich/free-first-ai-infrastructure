#!/usr/bin/env python3
"""Create an isolated key for a Windows client and save it on the VPS."""
import argparse
import os
from pathlib import Path
import tempfile

from configure import ACCESS, ALLOWED_ACCESS, dashboard
from probe import local_state


def provision(root, client):
    local_state(root)
    admin = dashboard(root)
    name = "free-first-windows-" + client
    keys = admin("/api/keys")["keys"]
    if any(key["isActive"] and key["access"] not in ALLOWED_ACCESS for key in keys):
        raise RuntimeError("An active key has unexpected model access")
    existing = [key for key in keys if key["name"] == name]
    if len(existing) > 1 or (existing and not existing[0]["isActive"]):
        raise RuntimeError("Check the existing account-specific key state")
    if existing:
        key = existing[0]
        if key["access"] != ACCESS:
            key = admin("/api/keys/" + key["id"], "PUT", {"access": ACCESS})["key"]
            if key["access"] != ACCESS:
                raise RuntimeError("Existing Windows key did not stay flash-only")
    else:
        key = admin("/api/keys", "POST", {"name": name})
        endpoint = "/api/keys/" + key["id"]
        try:
            result = admin(endpoint, "PUT", {"access": ACCESS})["key"]
            if result["access"] != ACCESS or not result["isActive"]:
                raise RuntimeError("New key policy did not persist")
        except Exception:
            admin(endpoint, "DELETE")
            raise
    output = root / "client-keys"
    output.mkdir(mode=0o700, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=output, delete=False) as data:
        data.write(key["key"] + "\n")
    os.replace(data.name, output / (client + ".key"))
    print(f"{client} key restricted to the approved production model")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/opt/9router-clean"))
    parser.add_argument("client", choices=("codex", "cursor"))
    args = parser.parse_args()
    provision(args.root, args.client)
