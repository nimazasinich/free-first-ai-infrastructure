# Owner decisions

The owner authorizes end-to-end gateway operations on the designated Windows workstation, VPS and GitHub repository. Routine operations may proceed autonomously. The [master plan](MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md) defines the current acceptance and cutover sequence.

- Preserve the existing native AIStudio2API installation, accounts, data, configuration and UI. Use its current health and authenticated API endpoints for minimal acceptance tests.
- Use the existing official clean 9Router with fresh state. Exclude all OmniRoute and legacy 9Router data and credentials from it.
- Use the existing Caddy and Edge Guard. Preserve unrelated services, VPN and monitoring.
- Keep routing default-deny. Prohibit paid fallback, Google Developer API, Vertex and any bypass of restrictions or quotas.
- Migrate clients after critical tests pass. Retire legacy 9Router, OmniRoute and its exclusive Redis after verifying consumer replacement, backup and rollback. Remove exclusive obsolete resources and preserve shared resources.
- Keep credentials, logs containing sensitive data and recovery material outside the public repository.
