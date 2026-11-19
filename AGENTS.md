# AGENTS.md — Codex Cloud Autonomous VPS Infrastructure Agent

## Instructions precedence
1. `OWNER_FINAL_DECISIONS.md` — highest priority owner-specific decisions and autonomy grant.
2. `MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md` — operational implementation protocol.
3. `CODEX_VPS_CONTEXT_NON_SECRET.md` — current/historical target facts; verify live.
4. `MASTER_PLAN_V7_CLEAN_9ROUTER_FREE_FIRST_AI_INFRASTRUCTURE_EN.md` — detailed technical reference, **superseded** where it requires per-phase owner approvals, local Windows operation, or continuation of legacy 9Router.
5. `EXECUTION_TRACKER.md` — state and evidence.

## Approach: operate, don't endlessly plan
The owner delegates end-to-end infrastructure work. Use SSH, Docker, systemd, network, GitHub, Caddy, available administrative APIs and appropriate supported tools. Do not stop after generating another abstract implementation plan. Work in testable increments, validate each change and recover from failures. Do not ask questions whose answers can be discovered on the target safely. No routine authorization gates for targeted operations in the approved scope.

## Protected asset
AIStudio2API is a fully functioning production deployment and must remain completely unchanged. Its endpoint can be read and invoked through supported existing APIs for necessary minimal tests; account/session/config modifications and migrations are forbidden. Existing unrelated system services stay intact.

## Rebuild from absolute zero
New official digest-pinned 9Router image + brand-new persistent directory/SQLite + new secret material + one deliberately configured AIStudio2API upstream. Do NOT copy anything from OmniRoute or the old custom 9Router. Retire both old routers and OmniRoute-exclusive Redis after validation. No added second central manager.

## Technical gates, not repetitive human approval gates
Prove application-level 9Router API auth, deny-by-default models, no unauthorized upstream forwarding, no paid fallback, and streaming/tool-calling integrity. Use stubs for negative/fault tests and minimal real probes. Keep rollback for cutover. When a target resource may be shared, identify ownership first. Stop only at the four immutable conditions in OWNER_FINAL_DECISIONS.md.

## Remote access
Cloud requires actual network routing and credential provisioning; a prompt alone cannot connect it. Check current environment capabilities. Use the fastest supported owner-authorized direct/private SSH method; obtain credentials through the environment's secure mechanism rather than the repository or chat. If a Cloud network feature is unavailable, offer one exact alternative (e.g. VPS-side Git pull/executor) and proceed where possible. Root/sudo administration is permitted for approved scope; a constrained non-root account is optional, not mandatory.

## Secrets
Credentials may be used by the agent **in the authorized runtime** for required API/SSH actions. Never place real secret values in source, issue descriptions, prompts, reports, CI logs or Git commits; avoid dumping secrets from filesystem or APIs. Don't block legitimate authenticated operations merely because they require credentials. No Google session import or state migration.

## Outputs
Commit and test infrastructure artifacts; keep a clear tracker and succinct evidence with timestamps and redaction. Report actual tested state, remaining failures, and completed cleanup. Avoid invented claims.
