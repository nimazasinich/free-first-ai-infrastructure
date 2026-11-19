# Execution Tracker — V9 Autonomous Deployment

Evidence is from the owner workstation SSH session on 2026-11-19. Codex Cloud still cannot open TCP 22. No secret values are recorded here.

| Phase | Purpose | Status | Evidence (timestamp, redacted) |
|---|---|---|---|
| P0 | Cloud-to-VPS connectivity; SSH/admin/API discovery; topology and baseline | PARTIAL | 2026-11-19: Workstation key login to `srv4503740909` as root succeeded. Codex Cloud probes returned connection refused before the server. AIStudio2API `/health` stayed HTTP 200. |
| P1 | Official digest/version verification | PASS | Official `decolua/9router` `0.5.119` `linux/amd64` digest `sha256:f98847db83f7ec9f1b36f78850a26c77c6502197163dff6eaa76d0ea199de3a0`. |
| P2 | Blank official 9Router install / new credentials and storage | PASS | Container `9router-clean` listens only on `127.0.0.1:20228`. New SQLite under `/opt/9router-clean/data`. `/api/health` returned `{"ok":true}`. No legacy database was imported. |
| P3 | Private Caddy-to-AIStudio2API integration | PASS | Private Caddy listener `172.20.0.1:20230` forwards only `/v1/models`, `/v1/chat/completions`, and `/v1/responses` to the local allowlist bridge, then to unchanged `127.0.0.1:2048`. |
| P4 | App auth and free-only deny-before-forward tests | PARTIAL | Missing client key returns 401. Requests for `gemini-3.1-pro-preview` and an unknown model stop at the bridge with 403 `model is not allowlisted`. The public model list still advertises built-in `mmf` and `oc` aliases, and `mmf/mimo-auto` returned 502 after an external bootstrap attempt. |
| P5 | Streaming/tool-calling/minimal real tests | PARTIAL | One canary model, `free/gemini-3.8-flash`, returned a real tool call and a stream ending in `[DONE]`. A plain short completion returned HTTP 200 with empty text and finish reason `length`. |
| P6 | Caddy endpoint integration, client cutover, rollback verification | PARTIAL | `r9` API policy now forwards to `127.0.0.1:20228`. Public `/v1/models` on `r9.185-221-237-84.sslip.io` answered 200 through the new router. The previous Edge Guard binary is saved as `/usr/local/sbin/edge-guard.before-9router-clean`. OmniRoute routes were not switched. |
| P7 | Remove OmniRoute, Redis exclusive assets, legacy 9Router and old data | NOT_RUN | Legacy containers are still running. They were not removed because the plain-text canary is only partial and OmniRoute still owns its own public hostname. |
| P8 | Recovery, as-built topology, handoff | PARTIAL | `9router-clean-bridge.service` is enabled. Container restart policy is still `no` until the plain-text completion is repeated successfully. |

AIStudio2API was not modified. No legacy 9Router or OmniRoute data was imported.
