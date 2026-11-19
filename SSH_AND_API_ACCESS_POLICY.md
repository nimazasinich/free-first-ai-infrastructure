# SSH + API Access — Broad Operational Mode for Codex Cloud

## Objective
Give Codex Cloud practical, persistent **project-scoped administrator capabilities** for the German AlmaLinux VPS without requiring a powered-on Windows host. The owner explicitly authorizes use of SSH and existing APIs, and does not want repetitive permission requests for routine work.

## Operational permissions
Codex may, after connecting using a real authenticated access path:
- Run arbitrary shell commands **needed for this project** with an authorized root/sudo-capable identity, inspect any relevant host path, manage Docker/Compose, systemd, logs, iptables/firewall rules, Caddy/Edge Guard config, internal ports/networks, and SSH diagnostics.
- Call existing AIStudio2API API endpoints for authenticated model discovery, health and low-volume completion tests, **without modifying that protected service or its account data**.
- Administer the **new** 9Router, including database initialization, secure configuration, access/API keys, providers, allowed models, routing and tests.
- Decommission and delete **exclusive legacy** 9Router/OmniRoute/Redis components after test-proven replacement; no copying old databases or settings into the new project.
- Use SSH tunnels, authenticated HTTP APIs and necessary package installations to accomplish the work, without asking for permission for each command.

## How access is actually established
1. Read current Cloud environment networking, secrets and private-access support. GitHub login alone is not server login.
2. Prefer an owner-approved management route supported by this Codex Cloud environment (Tailscale/private networking if available, or approved public SSH). Do not claim Tailscale or a particular tunnel is configured until a real test succeeds.
3. Configure SSH with a new authorized key/credential via the environment's supported secret input. A root/sudo-capable identity is permitted; the user may choose to provide a current authorized identity instead. Keep credentials off GitHub, chat messages and ordinary logs.
4. Verify server host key, SSH login, hostname, effective identity, `sudo` (if relevant), command execution, reconnection and access to the relevant management APIs. Record only redacted outcomes.
5. Keep client-independent continuity: use Git as the durable source of deployment code and store the actual deployed revision and rollback data on the VPS; ephemeral Cloud tasks must not be the only record.
6. Perform a live read-only inventory, then continue automatically with the owner-authorized implementation work if credentials/network and tool permissions permit.

### If the Cloud task cannot SSH
Precisely identify whether the missing piece is network egress, TCP tunneling, credential, SSH host policy or environment permissions. State one actionable fix, such as configuring the environment private network, adding an allowed SSH destination, or using a VPS-initiated reviewed Git deploy. Continue preparing/building/test artifacts in Cloud. **Do not claim a password or SSH key pasted into a chat automatically grants cloud VM access.**

## API boundary
The user authorizes calls to owner-administered endpoints and access needed for this infrastructure project. AIStudio2API must remain immutable. New 9Router administrative API and Caddy/Edge Guard management can be used to configure the gateway. Calling provider APIs must remain within account eligibility, provider terms and no-usage-billed constraints.

## Practical credential handling
- Secrets belong in the Cloud environment's supported private credential facility or host-side protected storage, never Git, AGENTS.md, prompts or task results.
- Agent code with access to a raw environment variable may be able to read its value; the owner has elected broad authority and accepts that access. Still redact outputs and avoid storing copies.
- Prefer SSH keys over passwords for unattended reconnect; verify host key; configure safe recoverability.
- Temporary access keys and test credentials may be generated or rotated for the new 9Router. Don't change AIStudio2API or unrelated credentials.

## Baseline tests
- SSH genuinely works from the Cloud environment; does not depend on Windows.
- Authorized elevated operations work when required.
- AIStudio2API health/model discovery works without changing its data.
- Docker/Caddy/Edge Guard can be inspected and changed on approved routes.
- No password/API key values appear in evidence files.
- After task restart, deployment state is recoverable from Git + the VPS.
