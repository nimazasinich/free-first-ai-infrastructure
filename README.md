# Free-First AI Gateway

The gateway exposes a single approved Google AI Studio Playground model through an official, digest-pinned 9Router. The existing AIStudio2API installation owns account selection, eligibility, quota and cooldowns.

```mermaid
flowchart LR
    Client -->|HTTPS and client key| Edge[Caddy and Edge Guard]
    Edge -->|Host loopback| Router[Official 9Router]
    Router -->|Dedicated Docker bridge and upstream bearer| Bridge[Private Caddy listener and SSE bridge]
    Bridge -->|Host loopback| Studio[Existing native AIStudio2API]
    Studio -->|Eligible account| Google[Google AI Studio Playground]
```

- [Authoritative execution plan](MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md)
- [Live verification and delivery status](EXECUTION_TRACKER.md)
- [Deployment and rollback runbook](docs/runbook.md)
- [Legacy retirement assessment](docs/legacy-retirement.md)
