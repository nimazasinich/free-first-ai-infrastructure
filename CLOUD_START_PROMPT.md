# Codex Cloud — Autonomous Execution Mission (copy body below)

You are the autonomous implementation agent for the GitHub repository `free-first-ai-infrastructure`. This is an authorized **execution** mission, not a planning-only task.

Read `OWNER_FINAL_DECISIONS.md`, `AGENTS.md`, `MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md`, `SSH_AND_API_ACCESS_POLICY.md`, `CODEX_VPS_CONTEXT_NON_SECRET.md`, `EXECUTION_TRACKER.md`, and then the V7 master plan as a technical annex. V9 explicitly supersedes restrictive V7/V8 approval requirements.

OWNER AUTHORIZATION: You may use SSH with an authorized root/sudo-capable identity, authorized APIs, Docker, systemd, filesystem, networking and Caddy/Edge Guard configuration to complete the end-to-end project on the German VPS. You may manage relevant files and services, install and configure the NEW 9Router, perform cutover and clean up exclusive old-9Router/OmniRoute/Redis resources after verifying the new path. Do not ask for separate consent for routine in-scope operations. Solve ordinary problems autonomously; use tests and rollback instead of repeated questions.

NON-NEGOTIABLE SCOPE: Completely preserve the existing AIStudio2API deployment, source, settings, accounts, session/database data, binaries, UI and systemd service. It is an existing upstream API only. Do not migrate any old 9Router or OmniRoute settings, databases, keys, accounts, logs, combos or custom patches. Use only an official clean digest-pinned 9Router image, new empty SQLite and newly generated keys. No unexpected usage-based API charges, no provider-prohibited routes, and no changes to unrelated services.

FIRST, check whether this Codex Cloud environment actually has SSH network connectivity and authorized credentials for the VPS. If it does, verify the host key and identity, then immediately proceed with P0-P8 including installation, integration, tests, cutover and legacy cleanup. If SSH is not yet provisioned, identify the exact missing Cloud environment networking/SSH credential step, prepare everything else in GitHub, and provide one concrete setup instruction; do not claim to have connected or deployed.

Run the mandatory model allowlist rejection and application-level API auth tests with synthetic stub upstreams before using real model capacity. Do minimal authorized end-to-end tests. Validate a rollback before cutting over. No per-command approval questions; only stop when a V9 immutable boundary is reached or a genuine credential/network access barrier cannot be resolved autonomously.

Commit implementation files and update `EXECUTION_TRACKER.md` with real redacted evidence. Report PASS/FAIL/PARTIAL/BLOCKED/NOT_RUN honestly and finish with the as-built topology, recovery commands and remaining blockers. Do not simply produce another abstract plan.
