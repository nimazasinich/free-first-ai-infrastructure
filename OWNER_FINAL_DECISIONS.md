# Owner decisions

The owner authorizes end-to-end gateway operations on the designated Windows workstation, VPS and GitHub repository. Routine operations may proceed autonomously. The [master plan](MASTER_PLAN.md) defines the current acceptance and cutover sequence.

- Preserve the **current fresh official AIStudio2API v0.3.12 installation**, its migrated account sessions, native settings and official UI. Do not restore removed historical source, old runtime or custom monitoring; verify health and account eligibility through the supported UI/API. The earlier fresh-reinstall decision supersedes preservation of the pre-reinstall installation.
- Use the existing official clean 9Router with fresh state. Exclude all OmniRoute and legacy 9Router data and credentials from it.
- Use the existing Caddy and Edge Guard. Preserve unrelated services, VPN and monitoring.
- Keep routing default-deny. Prohibit paid fallback, Google Developer API, Vertex and any bypass of restrictions or quotas.
- Migrate clients after critical tests pass. Retire legacy 9Router, OmniRoute and its exclusive Redis only after verifying consumer replacement, a safe reversible stop and an owner-authorized recovery method. No new AIStudio2API session backups are to be created without a new owner decision. Remove only proven exclusive obsolete resources; preserve shared services.
- Keep credentials, logs containing sensitive data and recovery material outside the public repository.
