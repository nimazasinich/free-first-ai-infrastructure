# Model eligibility and failover matrix

The tables below are the historical Phase 4 snapshot from before the fresh official release. See the [v10 checkpoint](master-plan-v10-execution.md) for current configuration and post-reinstall execution evidence. Account identifiers are omitted.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `CATALOG_VISIBLE` | Present in authenticated native `/v1/models` |
| `ACCOUNT_ELIGIBLE` | Bound in live `MODEL_ACCOUNTS` to at least one scoped account |
| `EXECUTION_VERIFIED` | Native request ledger shows HTTP 200 on the Playground channel |
| `COOLDOWN` | Active plan-limit cooldown observed at inspection time |
| `ACCESS_DENIED` | Explicit denial or out-of-scope binding |
| `BILLING_UNVERIFIED` | Playground history exists, but gateway enablement was withheld |
| `UNKNOWN` | Insufficient evidence |

## Live inventory snapshot

| Signal | Observed value |
| --- | --- |
| Native catalog size | 92 identifiers |
| Account slots monitored | 10 |
| Free-scoped accounts | 7 |
| Argon/Pro-scoped accounts | 3 |
| Scope overlap | 0 |
| Active cooldowns | 0 |
| Upstream channel evidence | `playground` on successful candidate traffic |
| Clean gateway providers | 1 (`free` → private bridge) |
| Clean gateway combos | 0 |
| Google Developer / Vertex env secrets | absent in the live AIStudio2API `.env` |

## Candidate matrix

| Upstream model ID | Tier | Catalog | Account | Execution | Billing for gateway | Gateway role |
| --- | --- | --- | --- | --- | --- | --- |
| `gemini-3.8-flash` | Free stronger | `CATALOG_VISIBLE` | Eligible via production traffic and Cursor alias mapping | `EXECUTION_VERIFIED` (Playground) | Playground-only path; no Developer/Vertex secret | **Production** (`free/gemini-3.8-flash`) |
| `gemini-3.5-flash-lite` | Free lightweight | `CATALOG_VISIBLE` | `ACCOUNT_ELIGIBLE` (7 free-scoped accounts) | `EXECUTION_VERIFIED` (Playground; recent multi-account 200s) | Playground-only; free scope; no metered provider configured | **Pilot only** (`free/gemini-3.5-flash-lite`) |
| `gemini-3.1-flash-lite` | Free lightweight | `CATALOG_VISIBLE` | `UNKNOWN` (not in live model-account bindings) | Partial native 200 history | `BILLING_UNVERIFIED` for gateway expansion | Disabled |
| `gemini-3.6-flash` | Free stronger | `CATALOG_VISIBLE` | `UNKNOWN` (unbound) | Sparse native 200 history | `BILLING_UNVERIFIED` | Disabled |
| `gemini-4-argon` | Subscription-entitled | `CATALOG_VISIBLE` | `ACCOUNT_ELIGIBLE` (3 Argon-scoped accounts) | `EXECUTION_VERIFIED` on native service | `BILLING_UNVERIFIED` for clean-gateway exposure; keep off Free-First keys | Disabled |
| `gemini-4-hydrogen` | Subscription-entitled | `CATALOG_VISIBLE` | Mapped in aliases; not Free-First scoped | Native 200 history | `BILLING_UNVERIFIED` | Disabled |
| Image / TTS / live / search variants | Specialized | Mostly `CATALOG_VISIBLE` | Mostly unbound for Free-First | Mixed | `BILLING_UNVERIFIED` or incompatible protocol | Disabled |

## Failover behavior

| Concern | Owner | Observed behavior | Free-First action |
| --- | --- | --- | --- |
| Account failover for the same model | AIStudio2API | Native ledger `attempts` shows another eligible Playground account after a per-account denial, then HTTP 200 | Do not duplicate; preserve upstream |
| Plan-limit cooldown | AIStudio2API + bridge | Safety monitor reported zero active cooldowns; bridge preserves `Retry-After` and turns stock 9Router retryable 502/503/504 into a single terminal 500 | Keep current bridge mapping |
| Model failover / combos | 9Router | Installed image supports combos, but production still has **zero** combos | No combo enabled; incompatible capability substitution avoided |
| Exhaustion | Both | When no eligible seat remains, clients receive a truthful upstream/gateway error | No silent paid fallback |

## Key and routing policy

| Credential | Allowed alias | Notes |
| --- | --- | --- |
| `canary` | `free/gemini-3.8-flash` | Unchanged production canary |
| `free-first-windows-codex` | `free/gemini-3.8-flash` | Unchanged |
| `free-first-windows-cursor` | `free/gemini-3.8-flash` | Unchanged |
| `free-first-pilot-lite` | `free/gemini-3.5-flash-lite` | New restricted pilot credential |

The private bridge allowlists exactly the production and pilot upstream IDs. Existing production keys still receive HTTP 403 for the pilot alias. The pilot key receives HTTP 403 for the production alias and for every other model.
