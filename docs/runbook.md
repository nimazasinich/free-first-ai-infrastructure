# Deployment and rollback

## Connect and verify before changes

From the designated Windows workstation, set `$sshConfig` to the existing operator-managed OpenSSH profile. Confirm the named host maps to the authorized VPS. Keep host-key verification enabled.

```powershell
ssh -V
ssh -F $sshConfig -G vps185-root |
    Select-String '^(hostname|user|port|stricthostkeychecking) '
ssh -T -F $sshConfig -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=12 vps185-root `
    'hostname; id -un; uname -s; cat /etc/os-release; date -u +%FT%TZ'
```

Require the hostname and account from the authorized inventory and AlmaLinux 9.8. Resolve any mismatch through the existing operator records before continuing. Obtain the running executable using the service MainPID, compare its SHA-256 against the executable in the digest-verified official release, and check native loopback health. Use read-only metadata for Docker image and router inventory.

Use the current V10 `scripts/acceptance.py ... policy` checker with the approved six-scope registry. It verifies both protected service journals over a common window and fails on unexpected active access. Earlier installation checkpoints used a smaller inventory and their corresponding checker revisions. Keep the server-side script version distinct from any reviewed repository revision.

## Layout

As of 2026-11-20 UTC the protected official `aistudio2api.service` runs v0.3.13 from `/opt/services/aistudio2api/releases/fresh-official-v0.3.12-20261119/aistudio2api`. The directory name dates from the fresh install. Its runtime is `/var/lib/aistudio2api-fresh` with account storage under `auth/`. Verify the active path with `systemctl show aistudio2api -p MainPID -p WorkingDirectory` and `readlink /proc/PID/exe`, then check loopback `/health` and the version in the official GUI. The Settings and Accounts pages provide configuration and readiness evidence. Preserve the runtime and sessions, and use verified clean-gateway revisions for router or bridge recovery. See the [current tracker](../EXECUTION_TRACKER.md).

- The public gateway's HTTPS virtual host serves `GET /v1/models`, `POST /v1/chat/completions` and `POST /v1/responses`. Caddy sets the authenticated Edge Guard policy `r9-api`, which forwards to host loopback port 20228. [Caddy route reference](../caddy/free-first.caddy)
- The pinned Docker image listens on port 20128, published only on loopback. Keep the existing `9router-clean-net` and existing `/opt/9router-clean/data` bind mount. Mount one gateway container on that network. [Compose](../docker/compose.yaml)
- The container can reach the private Caddy listener at `172.20.0.1:20230`. Caddy relays to the bridge at `127.0.0.1:20231` without delaying SSE. The bridge accepts the existing upstream credential and calls native AIStudio2API at `127.0.0.1:2048`.
- The bridge sends upstream 502, 503 and 504 failures to 9Router as terminal 500s and identifies the original status in the error. This avoids stock 9Router's automatic generation retries. The router may present a 503 with `Retry-After` while the upstream seat is cooling down. The bridge's header/idle timeout is 115 seconds, below Caddy's 120-second private response-header limit and the router's 130-second connection-to-headers limit.
- The live Caddy file is `/opt/edge/caddy/Caddyfile.public`. The Caddy fragment in this repository references equivalent gateway routes. Retain the deployed site's TLS and existing unrelated hosts when editing it.
- Application environment and runtime keys live in root-controlled files under `/opt/9router-clean`. The bridge receives `upstream.key` through systemd's `LoadCredential`. Store snapshots of the clean SQLite database outside Git.

## Install or update on the existing VPS

1. Confirm the approved digest is present, the dedicated network has gateway `172.20.0.1` and only the clean container is attached. Confirm Caddy, Edge Guard and native AIStudio2API are healthy.
2. Use the SQLite online backup API for the clean database, then run `PRAGMA quick_check` on the copy. Save the current bridge, service unit, Compose file and active Caddy file to a root-only local directory. On first Compose adoption retain the previous stopped clean container for reversible recovery.
3. Render [egress.nft](../docker/egress.nft) with a first line of `define clean_bridge = "BRIDGE_DEVICE"`, where the device is the Docker bridge that owns `172.20.0.1`. Use `nft -c -f` to check the rendered file. Install it as `/opt/9router-clean/egress.nft`. Install and enable [9router-clean-egress.service](../docker/9router-clean-egress.service). Keep its ordering before Docker and Caddy. Install [the Caddy drop-in](../caddy/docker-order.conf) under `/etc/systemd/system/caddy.service.d/` so the private Caddy listener follows Docker's bridge setup.
4. For an approved policy reconciliation, with the existing gateway available, run `python3 scripts/configure.py` as root on the VPS. The script verifies the clean provider, keeps production keys on `free/gemini-3.8-flash`, registers the production and pilot models, creates or refreshes the restricted `free-first-pilot-lite` key for `free/gemini-3.5-flash-lite`, and provisions the existing upstream bearer locally. See the [model eligibility matrix](model-eligibility-matrix.md).
5. Install [bridge.py](../bridge/bridge.py) at `/opt/9router-clean/bridge.py` and [the bridge unit](../bridge/9router-clean-bridge.service) under `/etc/systemd/system/`. Reload the systemd configuration, enable or restart the bridge, and wait for its loopback listener. Expect 401 from `/v1/models` without the upstream key. The bridge allowlists only the production and pilot upstream IDs.
6. Install the Compose file at `/opt/9router-clean/compose.yaml`. Validate with `docker compose -f /opt/9router-clean/compose.yaml config --quiet` so environment or credentials stay out of stdout. For the first adoption only, stop and rename the old **clean** container before starting Compose. Run `docker compose -f /opt/9router-clean/compose.yaml up -d --pull never` and wait for `http://127.0.0.1:20228/api/health` to return 200.
7. Run `python3 -m unittest discover -s tests -v`. As root on the VPS, run `python3 scripts/acceptance.py --public-url "$GATEWAY_URL" policy`, the bounded `pilot` suite for the lite credential, and the bounded `real` suite for production. Pass the public origin, for example `https://r9.185-221-237-84.sslip.io`, because the script appends `/v1/...`. A URL that already ends in `/v1` produces public 404 responses and is not a gateway failure. The negative test checks outbound bridge journal events before any positive probes. Use the public HTTPS hostname with certificate verification enabled. Verify the clean container's nftables counters and its inability to reach an unrelated host port or internet IP.
8. When restart acceptance is in scope, restart only the changed clean gateway components during a controlled window. Wait for the clean container and bridge health checks. Recheck the policy and a live public SSE request. Verify the native service PID and its HTTPS health.

The `policy` suite checks the stored scope of all four active keys and tests both Windows credentials against the local router. The bridge-journal count is valid during a quiet verification window without concurrent generation forwards. For generation, the probe records a successful Responses stream only after `response.completed`, and treats protocol error events and incomplete streams as failures.

Run [router-fault.cjs](../tests/router-fault.cjs) using `docker exec -i CONTAINER node - < tests/router-fault.cjs` in a disposable container of the pinned image. Start the fixture with `--network none --tmpfs /app/data --rm`, `FREE_FIRST_FIXTURE=1`, `REQUIRE_API_KEY=true`, and a dummy `INITIAL_PASSWORD`. The test creates fixture data through loopback and checks retry amplification, Combo isolation, tool calls and continuation, partial-stream failure, Anthropic Messages, and Gemini-native text translation and authorization. Its negative controls document semantic loss on an incompatible Combo and the limits of the pinned Gemini route. See the [V10 checkpoint](master-plan-v10-execution.md) for promotion gates. Use no production mounts or credentials.

## Recovery

- **Image/container failure:** Keep the egress guard in place. If the previously running clean container is saved, stop and remove the Compose instance and rename the saved clean container back to `9router-clean`. Start it and reuse only the same clean bind mount. Validate both the 401 and allowlisted route before restoring traffic.
- **Bridge failure:** Inspect `journalctl -u 9router-clean-bridge` for the `transport` records. Compare bridge timing with the client probe and the native request ledger. `first_chunk_ms` may include a heartbeat. Preserve the egress guard and auth/model restrictions. Use the current bridge/config from a known-good revision. Revert a failing change only to a verified safe revision. Phase 4 backups under `/root/free-first-phase4-backup-*` include the pre-pilot `bridge.py` and SQLite copy. If no safe revision is available, return a service error at the gateway or revert affected clients to their previously verified configuration. The historical bridge buffers SSE and is a diagnostic snapshot.
- **Pilot rollback:** Deactivate or delete the `free-first-pilot-lite` key in the local dashboard, remove `free/gemini-3.5-flash-lite` from the custom catalog if required, restore the previous bridge allowlist, restart the bridge, and rerun `policy`. Leave production flash keys unchanged.
- **Database recovery:** Shut down the clean container before replacing SQLite. Save the failed database and its WAL/SHM separately. Restore the clean, checked snapshot and original file ownership. After restarting, verify every active key is restricted before admitting traffic. An initial snapshot from before key hardening is for recovery investigation and requires reapplying the policy.
- **Edge routing failure:** Validate a candidate Caddy file with the service environment before any graceful reload. Restore the saved active file and reload if the gateway or unrelated routes regress. Keep the native AIStudio2API deployment intact.
- **Client migration:** Keep a verified prior configuration and a fresh scoped gateway key for the chosen client. Restore that client's prior configuration if the real application workflow fails. Keep retirement gated on consumer verification.

See the [Windows client installation and rollback section](client-migration.md#windows-installation-and-rollback) for the installed client launchers and credential handling. Before stopping legacy services, checkpoint their current restart behavior, verify the isolated backups, and account for scheduled jobs that could interact with stopped services. The [legacy assessment](legacy-retirement.md) lists the observed jobs and webhook.

## Controlled legacy stop and rollback

1. Establish that the remaining client, webhook and management workflows have a verified replacement or have been confirmed unused. Identify consumers of the OmniRoute vhost, IP-based API forwarding, WebSocket route, ops ingest, and legacy 9Router dashboard separately.
2. On the VPS, save a root-only copy of the matching root-crontab entries, active Caddy configuration, Edge Guard release and configuration, systemd units, Compose definition, and exact Docker image IDs and restart policies. Use SQLite's online backup API for the legacy databases. For Redis, record the persistence configuration and verify a consistent private backup of the Redis data volume. Keep all legacy recovery state outside the clean gateway.
3. Once gated, pause only confirmed legacy jobs and webhook producers so they cannot restart services or generate spurious errors. Save their prior state. Perform a reversible stop while retaining the existing containers and data.
4. Verify the approved Windows clients plus the clean gateway, native AIStudio2API, VPN and monitoring during the stop. To roll back, restore the previously recorded restart and scheduling state. Start Redis before OmniRoute, restore the candidate's egress before candidate-dependent endpoints, and restore any changed edge route from the tested Caddy configuration. Recheck both rollback and unrelated service health.
5. Remove only confirmed exclusive resources once the deliberate stop succeeds. Recheck the retained production routes, Docker network attachments, scheduled work, and service health after removal.

For a nondisruptive recovery rehearsal, start a disposable container of the same digest with `--network none --tmpfs /app/data --rm`. Override its entrypoint with a shell that waits for a readiness file and then runs `/entrypoint.sh node custom-server.js`. Use `docker exec -i` to write the verified SQLite backup to `/app/data/db/data.sqlite` and create that readiness file. Enable `REQUIRE_API_KEY` and run [router-recovery.cjs](../tests/router-recovery.cjs) inside the container via stdin. The probe uses the restored key in memory and prints only status. Stop the disposable container to discard the tmpfs.

## Unexpected active-key recovery

After the owner confirms the key's consumer inventory, authorize the exact model restriction or deactivation. Capture the prior dashboard policy and rollback decision in the private operator record. Keep the credential value in its approved store. If a consumer needs migration, verify its exact contract using a dedicated scoped key before changing the old key.

Use the supported 9Router controls and verify the persisted state. Repeat the approved registry and HTTPS catalog checks and the denied-forward policy window. On a confirmed regression, apply the explicitly agreed prior access policy through the dashboard and recheck affected clients. Resolve any temporary rollback exception before marking the production registry compliant. Keep database snapshot restoration for the separate database recovery procedure.

## Windows native settings rollback

Before a temporary native Cursor cutover, verify the exact live endpoint and selected model in Cursor Settings. Confirm that the recovery credential is usable by the same Windows user and matches the prior provider. Keep the settings snapshot and protected credential in the existing private recovery directory. Proceed with a native Agent test once the compatibility, billing and recovery gates pass.

If the cutover fails, restore the original provider URL, credential and model selection through Cursor's supported GUI, reload the app and verify the effective settings and persistent Free-First MCP registration. Record settings recovery and any separately authorized generation through the restored provider independently. The recovered baseline for the current checkpoint is `https://aistudio.185-221-237-84.sslip.io/v1` with the native `cursor-combo-vps` alias. See the [current tracker](../EXECUTION_TRACKER.md) for open gates.
