# Legacy retirement assessment

**BLOCKED** as of 2026-11-19.

- The dedicated Codex profile and the exact supported saved Flash profile now use the clean gateway. Cursor has a persistent clean MCP registration. The original Windows configurations still contain old combo and management integrations. The workstation has 95 remaining OmniRoute profiles and two disabled matching scheduled tasks. [Client dependency matrix](client-migration.md)
- Caddy still has legacy OmniRoute API and UI routes, an OmniRoute hook, and a legacy 9Router dashboard route on a separate listener. Edge Guard still references their upstreams. An empty socket sample does not establish the absence of consumers.
- The legacy candidate has a dedicated data mount, private bridge and egress service. OmniRoute and its Redis share an exclusive-looking Compose network, with Redis attached to a named volume. Treat exclusivity as provisional until timers, hooks, mounts and other callers are reconciled.
- The legacy candidate, OmniRoute and Redis were observed running. Both legacy networks contained only their named router components during inspection. The Redis data volume belongs to the OmniRoute Compose project. The candidate retains a separate bind mount and active egress service.
- The VPS has active OmniRoute root-crontab entries for nightly backups and a five-minute resource watcher. The configured OmniRoute webhook was enabled and points to the live ops ingest route. The latest recorded webhook delivery and ingest event were on November 8 UTC.
- A read-only usage check recorded two OmniRoute generation rows and zero legacy 9Router generation rows in the last seven days. The most recent OmniRoute generation was November 17 UTC. These counts do not cover every admin, dashboard, or WebSocket consumer.

No controlled stop or resource deletion has been performed. The incomplete application tests and unresolved OmniRoute consumers remain retirement gates.

For retirement, first verify replacement client workflows and identify remaining service, route, webhook and scheduled-job owners. Create and verify a root-only recovery copy for each exclusive data store. Perform reversible container stops with current restart semantics documented, rerun gateway and unrelated health checks, and verify the restore sequence. Remove only identified exclusive resources after those checks.
