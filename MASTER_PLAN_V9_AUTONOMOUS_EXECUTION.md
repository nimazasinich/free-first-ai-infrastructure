> **HISTORICAL / SUPERSEDED BY [MASTER_PLAN v10](MASTER_PLAN.md).** This v9 document describes the initial gateway rollout. It is not the current source of deployment paths, account/runtime state or model/failover policy after the 2026-11-19 official AIStudio2API reinstall.

# Free-First gateway master plan

## Operating scope

Use the owner's existing Windows SSH alias with strict host-key checking and the existing GitHub authentication. The authorized gateway uses Caddy and Edge Guard, the existing clean official 9Router, a private authenticated bridge, and the existing native AIStudio2API service. The approved starting model is `free/gemini-3.8-flash`.

- AIStudio2API owns eligibility, scheduling, quota management and cooldown. Use its existing APIs for bounded verification and preserve its installation, configuration, database, accounts, sessions and UI.
- 9Router handles client authentication, aliases and routing. Keep the initial deployment to one approved provider and zero combos. Fail closed on upstream errors. Enable additional targets only after explicit approval, billing eligibility and full compatibility verification.
- Build no paid fallback, Google Developer API or Vertex integration. Use only existing permitted Playground capacity. Keep all prior router data outside the clean installation.
- Preserve the VPN, monitoring and unrelated edge routes. Keep credentials and private recovery data on authorized systems.
- The [owner decisions](OWNER_FINAL_DECISIONS.md) establish project authorization. This plan is the current technical specification. The [tracker](EXECUTION_TRACKER.md) records observed progress and open gates.

## Execution gates

1. Verify SSH, GitHub, digest, existing storage and dependency inventory.
2. Apply restricted API keys and explicit model catalog. Verify method, route and model policy on live ingress, with zero upstream forwards for rejects. Maintain a network deny boundary for the dedicated Docker network.
3. Verify Caddy and Edge Guard to 9Router, private bridge authentication and direct upstream compatibility. Measure direct and gateway streaming, including first event, first content and stream completion. Verify structured tool-call arguments and a tool result continuation.
4. Verify restart, scoped resource use, synthetic failure handling and the rollback procedure. Use real minimum-size requests only for positive acceptance. Record the observed status for each test.
5. Move one compatible, known client using a fresh scoped key. Verify that client's real API or agent workflow. Expand after acceptance and retain rollback for each client.
6. Resolve every legacy consumer and prove ownership of Docker resources, edge routes, integrations and scheduled jobs. Back up exclusive state locally and verify recovery before controlled retirement. Remove exclusive obsolete resources after the stop checks and preserve shared services.
7. Commit the as-built configuration, tests, tracker and runbook. Publish only credential-free results.
