# MASTER PLAN V9 — Autonomous Cloud-Led Deployment (Executive Operating Specification)

**Status:** Owner-authorized project execution instructions. Real VPS connection remains dependent on configured access. **The detailed engineering reference is the included Master Plan V7**, overridden by these V9 instructions where inconsistent.

## A. End state
- External clients -> current Caddy/Edge Guard -> pristine official 9Router Docker -> private authenticated bridge -> untouched AIStudio2API systemd -> authorized Google AI Studio accounts / Playground.
- Only one central 9Router; no OmniRoute, OmniRoute Redis, legacy patched 9Router, LiteLLM, CLIProxyAPI, or extra inference-network proxy in target infrastructure.
- No migration or reuse of legacy router data/keys/accounts/configurations. Fresh identities and blank SQLite, verified official image digest.
- Full normal API, streaming and coding-tool functionality where actual upstream capabilities support it; free-only and fail-closed.

## B. Access and mandate
The owner authorizes the agent to connect via SSH and use administrative APIs and SSH/sudo for all **in-scope** tasks, including Caddy changes, Docker deployment, cutover, retirement and destruction of *exclusive obsolete router resources*, without asking for per-command permission. Implement in the Cloud-to-VPS workflow when credentials/network are actually provisioned. Do not impose V7/V8 non-root-only or read-only-first-forever restrictions. Initial baseline remains read-only for evidence; subsequently act.

## C. Work phases with technical pass/fail gates

| Phase | Deliverable | Must verify |
|---|---|---|
| P0 | Live SSH access and topology | cloud-to-VPS login works, identity + host key verified; full process/port/dependency map; protected baseline captured |
| P1 | Official 9Router artifact selection | upstream version and immutable digest, target amd64, license/source, auth/custom-provider support; reject unverified build |
| P2 | Fresh isolated installation | new container, new network/persistent 0700 SQLite, new secrets, no imported legacy state, no public unintended admin port |
| P3 | Private upstream connectivity | correct Docker-to-loopback API path via Caddy bridge or equivalent, 9Router client auth + upstream auth, no changes to AIStudio2API |
| P4 | Free-only security proofs | invalid/missing API keys rejected *by 9Router*; disallowed models rejected before stub upstream is called; no billable/prohibited route possible |
| P5 | Functional regression tests | one minimal real request, streaming and structured tool-calling where supported; simulated failures, no retry storm; baseline overhead acceptable |
| P6 | Caddy routing + controlled cutover | correct endpoint + rollback, old and unrelated Caddy paths preserved, new keys configured on intended clients |
| P7 | Decommission and cleanup | verify obsolete route consumers and shared resources; stop then remove exclusive OmniRoute, Redis, legacy 9Router and old config/data safely; no legacy data imported into new gateway |
| P8 | Recoverability and as-built handoff | restart persistence, Docker health, logs, Git commit, precise final port map, evidence and operation runbook |

Each phase requires **technical verification, not another owner approval prompt**. On normal errors debug and retry safely. Do not intentionally exhaust provider quotas, brute-force credentials, or expose the API to unauthenticated clients.

## D. Deployment architecture rules
- Prefer Docker with official digest-pinned 9Router; use its native supported configuration; do not use patched/locally modified legacy images.
- Keep systemd AIStudio2API and related state entirely untouched, including GUI and accounts. It currently binds `127.0.0.1:2048`; verify actual listener, and bridge the connection privately without changing this bind.
- Existing Caddy + Edge Guard remain in place; agent can create/update narrowly scoped routing rules needed for new gateway, validating config and preserving unrelated virtual hosts.
- New API authentication must be validated independently of edge authentication, particularly because of reported 9Router REQUIRE_API_KEY/enabledModels problems. Use mock upstream counters for negative tests.
- Provide separate keys for client use; use only models confirmed supported by AIStudio2API; no paid fallback. No assumption that advertised model equals sustained available capacity.
- Treat a model/tool failure as a functional fault, not as a reason to rewrite AIStudio2API.

## E. Old installation cleanup (approved scope)
Use inventories to identify what belongs exclusively to OmniRoute/Redis/old 9Router: Docker containers/images/volumes/networks, dedicated scripts/units/edge routes and logs. Never copy their data into the new installation. If uncertain whether something is shared, inspect first. Prefer a short reversible cutover while verifying; once new path succeeds and exclusive ownership is confirmed, execute complete cleanup. This is pre-approved, not a request for additional consent. Preserve the current VPN, unrelated monitors and other services.

## F. Immutable boundaries
1. **No changes to AIStudio2API**, its configuration, accounts, sessions, binaries, UI, data or deployment; API read/inference calls allowed.
2. **No unexpected money costs** or unauthorized usage-based API routes, no circumvention of provider quotas or access conditions.
3. Do not damage shared/unrelated infrastructure or delete unknown assets.
4. The agent must not fabricate SSH/API access, executed commands or test results.

## G. Reporting and deliverables
Repo: `docker/compose.yaml`, `caddy/` partial route with safe validation, `scripts/` preflight/deploy/rollback/cleanup, `tests/` auth/allowlist/mock/functional fixtures, `.github/workflows/` CI as relevant, `docs/` as-built/risks/runbooks. Prefer commits/PRs; record the actually deployed revision. `EXECUTION_TRACKER.md` keeps timestamped real PASS/FAIL/PARTIAL/BLOCKED/NOT_RUN evidence. Never include production secrets in repo or reports. Complete the infrastructure, not just another planning document.
