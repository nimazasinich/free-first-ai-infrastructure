# VPS CONTEXT FOR CODEX CLOUD — NON-SECRET

**Purpose:** Architectural and operational context for the `free-first-ai-infrastructure` GitHub repository. This document contains historical non-secret observations. Live operational authority comes from OWNER_FINAL_DECISIONS.md and MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md; this file contains no credentials.

**Observed:** 2026-11-19 via owner-authorized read-only inspection. Treat as historical; independently recheck during the approved deployment phase.

## Target outcome

Create a clean, secure, free-first AI API infrastructure:

`Cursor / Codex / future clients -> existing Caddy + Edge Guard -> newly installed official 9Router (Docker) -> existing, protected AIStudio2API (systemd) -> eligible Google AI Studio accounts -> Playground`.

9Router is the only central API router. No OmniRoute, LiteLLM or CLIProxyAPI in the target architecture. No additional proxy or VPN in the AI request path by default.

## Protected production boundary

- **AIStudio2API is complete and protected.** Do NOT change its source, binaries, configuration, databases, sessions, account information, service unit, environment files, deployment or UI. Do not import any of its secrets into GitHub or Codex Cloud. Only inspect read-only metadata when authorized; integrate through the existing authenticated API.
- Existing Caddy and Edge Guard remain the HTTPS ingress. Codex is pre-authorized to make narrowly scoped routing changes for this project with validation and rollback.
- Preserve unrelated existing VPN, network and monitoring services.

## Server inventory (historical; no secrets)

| Property | Observation |
|---|---|
| VPS public address | `185.221.237.84` |
| Hostname | `srv4503740909` |
| OS | AlmaLinux 9.8 |
| Compute | About 2 vCPU; 3655 MiB RAM |
| Memory | About 1777–1796 MiB available at inspection; 1586–1588 MiB swap used out of 4095 MiB |
| Disk | 58 GB root, 36 GB used, 20 GB available (65%) |
| Main AIStudio2API API listener | `127.0.0.1:2048` on VPS host; observed `/health` HTTP 200 |
| Other AIStudio2API-related listeners | `127.0.0.1:2050`, `127.0.0.1:2148`, `127.0.0.1:2150`; exact roles require identification |
| Edge | Caddy via systemd, Edge Guard existing |
| Legacy OmniRoute | Docker; host `127.0.0.1:20128` used by OmniRoute; dedicated Redis observed |
| Legacy 9Router | Container `9router-candidate`, local modified image, container port `20128/tcp` not published directly |
| Legacy 9Router network | `9router-stage-internal`, marked Docker `internal=true`; direct access to host bridge `:2048` refused |
| Existing auxiliary service | `9router-gemini-egress.service` on bridge port `20139` was observed; its purpose, compliance and dependencies require audit |

Observed existing `r9` HTTPS routing traverses Caddy/Edge Guard; an external HTTP 401 does NOT prove 9Router application-level authorization.

## Updated authority (V9)

Codex is authorized to configure a working Cloud-to-VPS SSH method, use an approved root/sudo-capable administrative identity and authorized service APIs, operate all project-related Docker/Caddy/systemd files, and fully deliver the **new** 9Router without per-command approval prompts. Access still needs real environment/network/credential configuration. The protected AIStudio2API remains immutable; unrelated services stay untouched; no paid/provider-prohibited API routes.

Read `OWNER_FINAL_DECISIONS.md`, `AGENTS.md`, `MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md`, `SSH_AND_API_ACCESS_POLICY.md` and `EXECUTION_TRACKER.md`. The V7 master plan is retained as a technical appendix; restrictive V7/V8 approval gates are superseded.
