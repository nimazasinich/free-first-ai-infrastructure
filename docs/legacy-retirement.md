# Legacy retirement assessment

**BLOCKED** as of 2026-11-19 15:36 UTC. No container, route, cron job, webhook, or live MCP registration was stopped or deleted. Native Cursor model-provider work is deferred and is not a retirement gate.

## Dependency matrix

| Component | Consumer | Required capability | Last confirmed activity | Replacement | Risk | Classification | Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cursor MCP `omniroute-germany` | Live Cursor processes launching `Launch-OmniRoute-Mcp.ps1` / `diagnostic-mcp-v3.mjs` | Multi-combo generation and OmniRoute management tools | Running now; Nov 17 generations match `code-fast-verified` defaults | Free-First MCP covers only Flash catalog/chat | High | ACTIVE_REQUIRED | Keep |
| Cursor MCP `9router-candidate-combos` | Live Cursor processes launching `9router-cursor-mcp.mjs` | Legacy candidate combo tools | Processes running now; candidate usage last `ok` day 2026-11-11 | None in one-model gateway | High | ACTIVE_REQUIRED | Keep |
| Cursor MCP `free-first-gateway` | Live Cursor Free-First launcher | Restricted Flash generation | Running now; Agent MCP PASS earlier today | N/A | Low | ACTIVE_REQUIRED | Keep |
| Codex profiles `free-first-gateway`, `gemini-gemini-3-8-flash` | Windows Codex scoped clients | Exact `free/gemini-3.8-flash` | Migrated and regression-tested | Already on clean gateway | Low | ACTIVE_REQUIRED | Keep |
| 95 OmniRoute Codex `*.config.toml` profiles | Saved Codex configs | 45 combo aliases, 46 provider-specific models, 4 named aliases | Mostly inactive saved configs; not 95 live callers | Only exact Flash was eligible; already migrated | Medium if mass-deleted | CONFIGURED_BUT_UNUSED | Keep; do not mass-convert |
| Argon `argon-aistudio` / `argon-aistudio-ssh` | Direct AIStudio Codex profiles | `gemini-4-argon` | Profiles present | Outside OmniRoute retirement | Medium | ACTIVE_REQUIRED | Keep |
| Windows task `Cursor-9Router-PrivateTunnel` | Historical tunnel maintainer | Private tunnel | Status Disabled | Free-First HTTPS path | Low | OBSOLETE_VERIFIED | Leave disabled |
| Windows task `OmniRoute Gemini Geo Guard` | Historical geo guard | Geo routing helper | Status Disabled | None required for clean gateway | Low | OBSOLETE_VERIFIED | Leave disabled |
| OmniRoute container + Redis | MCP, Caddy `omni.*`, webhook, cron | Multi-provider generation and ops | Container healthy; 321 provider-test rows today; last gen 2026-11-17 | Incomplete | High | ACTIVE_REQUIRED | Keep |
| `omni-ops-webhook.service` | OmniRoute custom webhook record | Failure/quota ingest | Enabled; last delivery 2026-11-08 02:39:50 UTC HTTP 204 | None verified | Medium | ACTIVE_REQUIRED | Keep while OmniRoute runs |
| Root cron nightly backup / 5-min resource watch | OmniRoute ops | Backup and RAM alerts | Registered and owned by OmniRoute | Keep while OmniRoute runs | Medium | ACTIVE_REQUIRED | Keep |
| `9router-candidate` + `9router-gemini-egress.service` | Candidate MCP and egress | Legacy candidate API | Container running; egress active; usage idle since 2026-11-11 | Incomplete | High | ACTIVE_REQUIRED | Keep |
| Caddy OmniRoute / candidate / webhook routes | Public and edge consumers | Host routing | Present in `/opt/edge/caddy/Caddyfile.public` | Incomplete | High | ACTIVE_REQUIRED | Keep |
| Clean `9router-clean` stack | Free-First clients | Restricted Flash gateway | Healthy; policy PASS | N/A | Low | ACTIVE_REQUIRED | Keep |
| AIStudio2API | Protected upstream | Native Playground API | PID `1994530` since 2026-11-18 17:35:38 UTC | Must not change | Critical | ACTIVE_REQUIRED | Do not modify |

## Why retirement remains blocked

- Live Cursor still loads OmniRoute and candidate MCP servers. Their required capabilities are multi-model or management surfaces that the one-model Free-First gateway does not replace.
- The Nov 17 OmniRoute Chat rows still match the live `omniroute_combo_chat` defaults (`combo/code-fast-verified`, 256 completion tokens). Exact process attribution remains incomplete, so the service stays required.
- Candidate usage is idle after 2026-11-11, but the candidate MCP process and egress unit are active. Idle tables alone are not ownership proof.
- Webhook and both OmniRoute cron jobs remain owned by the still-running OmniRoute deployment.
- No additional Flash-compatible Codex consumer was found to migrate. Remaining flash-named OmniRoute profiles use other model IDs and were not remapped.

## Resource baseline if retirement becomes unblocked

Observed at 2026-11-19 15:36 UTC, before any stop:

- Root filesystem: 38G used, 18G available (69%).
- OmniRoute about 402 MiB RAM, Redis about 13 MiB, candidate about 23 MiB, clean gateway about 108 MiB.
- Disk: `/opt/omniroute` 2.0G, `/opt/9router-migration` 179M, `/opt/9router-clean` 2.3M, `/opt/aistudio2api` 3.1G.
- Measured reclaim this phase: none.

## Retirement procedure when gates clear

1. Prove each remaining ACTIVE_REQUIRED consumer has a verified replacement or is unused.
2. Save root-only copies of crontab, Caddy, Edge Guard, systemd units, Compose definitions, image IDs, restart policies, and SQLite/Redis backups.
3. Pause confirmed jobs/webhook producers, then reverse-stop only the cleared service while retaining containers and data.
4. Recheck Free-First clients, AIStudio2API, VPN, and monitoring.
5. Remove only proven exclusive resources after a successful deliberate stop and restore rehearsal.
