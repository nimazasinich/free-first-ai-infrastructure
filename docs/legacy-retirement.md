# Legacy retirement assessment

**BLOCKED** as of 2026-11-19.

- Codex and Cursor configurations still declare the OmniRoute bridge and legacy 9Router combo MCP servers. The new model canary exposes one approved model and zero combos. Compatibility with those deployed client workflows requires separate verification.
- Caddy still has legacy OmniRoute API and UI routes, an OmniRoute hook, and a legacy 9Router dashboard route on a separate listener. Edge Guard still references their upstreams. An empty socket sample does not establish the absence of consumers.
- The legacy candidate has a dedicated data mount, private bridge and egress service. OmniRoute and its Redis share an exclusive-looking Compose network, with Redis attached to a named volume. Treat exclusivity as provisional until timers, hooks, mounts and other callers are reconciled.
- The legacy candidate, OmniRoute and Redis were observed running. No legacy state was copied into the clean gateway.

For retirement, first verify replacement client workflows and identify remaining service, route, webhook and scheduled-job owners. Create and verify a root-only recovery copy for each exclusive data store. Perform reversible container stops with current restart semantics documented, rerun gateway and unrelated health checks, and verify the restore sequence. Remove only identified exclusive resources after those checks.
