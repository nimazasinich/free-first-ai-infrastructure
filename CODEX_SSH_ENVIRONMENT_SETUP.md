# Codex Cloud SSH setup — verified path to the German VPS

Read this before any SSH attempt. It replaces guesswork about port 22. No secret values belong in this file, in Git, or in chat.

## What is already true (checked 2026-11-19 from the owner workstation)

The VPS SSH service is up. Codex Cloud is blocked on the network path, before authentication.

| Check | Result |
|---|---|
| TCP `185.221.237.84:22` from the owner workstation | Open |
| Login `root` with the existing ed25519 key | Success |
| `sshd` listen addresses | `0.0.0.0:22` and `[::]:22` |
| Host firewalld | `ssh` allowed (`tcp dport 22 accept`) |
| `iptables` INPUT policy | `ACCEPT` |
| fail2ban | Not installed |
| Tailscale on the VPS | Not enrolled |
| Codex Cloud and its outer executor | `Connection refused` before auth |

`Connection refused` from Cloud does not mean the password was wrong. The password was never sent. Do not try a password again.

`wg0` (UDP `51820`) is an existing owner tunnel. Do not change it, add a peer, or treat it as a Codex network.

## Connection parameters

- Host: `185.221.237.84`
- Port: `22`
- User: `root`
- Auth: the ed25519 key already in `/root/.ssh/authorized_keys`
- Authorized public-key fingerprint: `SHA256:6KUp6EDfXfMt5aBx9zba5MeZWNLM0b1peQOjKV6pbLI` (`omniroute-vps-185`)
- Trusted server host key (ED25519): `SHA256:Dxz0XqbucXGhGafcC2VX8AV1/FABqQ7rZDZ6jXo4Clc`

Pin this exact host key. Refuse the connection if the fingerprint differs:

```
185.221.237.84 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGWbFNbQj8RfjJyDBjC+adtxrTGlrV4jwcNgUrR4wLso
```

## What the owner must attach in Codex Cloud

1. Rotate any root password that was pasted into a chat. Do not put the new password here or in the task prompt.
2. In the Codex Cloud environment credential binding, install the private half of the key whose public fingerprint is `SHA256:6KUp6EDfXfMt5aBx9zba5MeZWNLM0b1peQOjKV6pbLI`.
3. Keep that private key only in the Cloud secret store. It is already the key the owner workstation uses. Do not generate a second key: Cloud cannot install a new `authorized_keys` line until this path works.
4. In the VPS provider firewall (not the AlmaLinux firewall), allow inbound TCP `22` from the Codex Cloud egress address. The operating system already accepts TCP `22` from any source. If the provider firewall stays closed to Cloud addresses, SSH will keep returning `Connection refused` and no credential can fix it.

## What Codex must run after those two bindings exist

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
printf '%s\n' '185.221.237.84 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGWbFNbQj8RfjJyDBjC+adtxrTGlrV4jwcNgUrR4wLso' > ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
# SSH_PRIVATE_KEY is the environment secret. Never echo it.
install -m 600 /dev/null ~/.ssh/id_ed25519
printf '%s\n' "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile=~/.ssh/known_hosts \
  -o ConnectTimeout=12 root@185.221.237.84 'hostname; id; sudo -n true'
```

Success is a real shell on `srv4503740909` as `uid=0(root)`. Then continue P0–P8. Shred the temporary key file when the task ends if the environment would otherwise persist it in a repo or log.

If the result is still `Connection refused`, stop SSH attempts. Record P0 as BLOCKED. Do not change `sshd`, firewalld, `wg0`, or AIStudio2API to chase the refusal. The missing piece is the provider-edge allow, not another login method.

## Fallback while Cloud still cannot open TCP 22

Prepare and commit repository artifacts only. The owner workstation already has working root SSH and can pull those commits and run the deployment on the VPS. Do not claim that Cloud deployed anything.

AIStudio2API stays unchanged in every path.
