# Free-First gateway operations

Use [the master plan](MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md) for scope and acceptance and [the runbook](docs/runbook.md) for deployment and recovery. Read [the tracker](EXECUTION_TRACKER.md) and verify live conditions before changing anything.

- Use the existing Windows OpenSSH profile and strict host-key checking. Use existing GitHub authentication and keep changes reviewable.
- Reuse the existing digest-pinned official 9Router and clean SQLite state. Keep all legacy router data out of it.
- Treat AIStudio2API as a protected existing service. Limit operations to read-only health checks and minimal authenticated API probes. Leave its deployment, code, configuration, UI, accounts, sessions and databases intact.
- Keep one approved upstream and deny unapproved routes and models. Use restricted client keys. Preserve the private bridge and the dedicated container egress policy. Use synthetic failures for rate limits, outages and other disruptive cases.
- Advance cutover only after the critical acceptance gates pass. Identify consumers, validate rollback, and preserve unrelated services before retiring exclusive legacy resources.
- Keep tokens, environment files, keys, database snapshots and raw requests outside Git. Update the tracker with observed PASS, FAIL, PARTIAL, BLOCKED or NOT_RUN results.
