# OWNER FINAL DECISIONS — V9 / FULL OPERATIONAL AUTHORITY

Date: 2026-11-19. This document supersedes the more restrictive onboarding and approval wording in V7/V8. It expresses the owner's authorization **for this specific infrastructure project**, subject to the technical ability to connect and any real platform approval controls. It is not a credential or a network connection by itself.

## Fixed architecture

Clients -> existing Caddy + Edge Guard -> **new, pristine official 9Router Docker instance** -> private authenticated API path -> **existing unchanged AIStudio2API systemd instance** -> authorized Google AI Studio Playground.

- **AIStudio2API is protected in place.** Do not alter its code, binary, service unit, deployment, UI, settings, account inventory, tokens, databases, sessions, configuration, or stored data. You may use its existing authenticated APIs to discover models/health and make minimal authorized functional test requests. Do not copy its accounts/session database into the new project.
- **OmniRoute is unwanted.** Decommission its dedicated containers, Redis, webhooks, Caddy routes, data volumes, images and obsolete files after checking that each resource is exclusive and the new route passes acceptance. Remove its legacy data after safe verification. Do not reuse OmniRoute data in the new system.
- **Legacy 9Router is unwanted.** It may be inspected to map consumers and dependencies, but do not copy/import any settings, API keys, providers, models, combos, databases, accounts, request history, patches or other data into the new 9Router. Retire and clean up its dedicated components after successful cutover.
- **9Router NEW** is an unmodified official digest-pinned image, with entirely fresh SQLite state, independent keys and configuration, and a single initial approved AIStudio2API upstream. Add no second gateway, LiteLLM, paid provider, proxy chain or prohibited OAuth integration.
- **No unanticipated usage-based billing:** default-deny route/model policy; fail closed for unknown, paid, prohibited and incompatible destinations. Do not bypass provider restrictions or quotas.
- Preserve unrelated VPN, monitoring, Caddy/Edge Guard and other services except the specific approved routing edits necessary for this project.

## Owner's autonomy grant

The owner explicitly wants **broad, autonomous administrative execution rather than repeated per-command approval requests**. Once Codex has a working owner-authorized access method, it may:

- Connect over SSH, inspect and operate the VPS filesystem, packages, processes, systemd, Docker, networks, logs, firewall and Caddy/Edge Guard routing where necessary for this project's installation and cleanup.
- Use existing authorized APIs and management endpoints, discover supported operations, authenticate using securely provided credentials, create/configure new 9Router credentials, and perform end-to-end tests.
- Install necessary dependencies; build and test the GitHub repository; create isolated staging; manage ports, services and configuration *outside the protected AIStudio2API installation*.
- Change the Caddy/Edge Guard routes required for the **new** gateway, provided existing unrelated routes are preserved and the change is validated and reversible.
- Carry out cutover, retirement and eventual permanent cleanup of **identified legacy-only** OmniRoute/Redis/old-9Router resources after confirming successful replacement and no unrelated consumers.
- Choose robust authorized SSH transport (private tailnet if available; otherwise verified direct SSH or equivalent), use an authorized administrator/sudo identity, and maintain working access without Windows dependency.
- Run the complete delivery workflow without asking permission for each command, edit, restart or standard verification step; fix ordinary technical blockers autonomously.

**This is permission for the stated project, not permission to change unrelated production assets.** Preserve access and make targeted changes. Avoid irreversible action where the target or ownership is uncertain; if an unexpectedly shared or critical resource is implicated, stop that specific action and report it, while continuing independent work.

## Only immutable stop conditions

1. Changing AIStudio2API's protected application/state, including account or session material.
2. Enabling real paid, metered, usage-billed or provider-prohibited model/API routes, or bypassing restrictions.
3. Deleting/altering an unrelated/shared resource or disabling the owner's independent VPN/services without a proven replacement.
4. An operation requiring a credential, network capability, human approval or tool permission **not actually supplied**. State the exact missing prerequisite; do not pretend permission words create connectivity.

Backups and snapshots may be used for safe rollback but must be kept isolated from the fresh 9Router, must not be committed to GitHub or uploaded to Codex task artifacts, and should be deleted with the legacy data when the verification and cleanup conditions are met.

## Reporting

Act first within this authority, then report evidence concisely. Use PASS / FAIL / PARTIAL / BLOCKED / NOT_RUN. Never claim successful SSH, API use, deployment or tests without real evidence. Redact credentials and sensitive account data from all outputs.
