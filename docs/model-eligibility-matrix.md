# Model eligibility and failover matrix

## Live catalog and scope recheck, 2026-11-20 UTC

At approximately 22:55–22:59 UTC the official AIStudio2API v0.3.13 console displayed 50 model records and 10 accounts, including seven Free and three Pro. Its authenticated OpenAI-compatible catalog listed 105 IDs, including aliases. The production bridge exposed three native model IDs. The settings showed Playground enabled, Build and hedging off, no model channel override rows, and fake streaming off. The scopes below are the configured account candidate sets. Per-seat entitlement, readiness and billing can change.

- **Flash 3.8** (`free/gemini-3.8-flash`) is the approved production Chat Completions and Responses route. The native dialog showed automatic selection from all eligible accounts. Canary, Cursor MCP and Codex showed the exact Flash catalog over HTTPS. Historical live evidence covers completion, streaming and structured tools, including Cursor Agent MCP continuation. Fresh native Cursor and installed Codex Responses continuation lack an accepted result.
- **Flash-Lite 3.5** (`free/gemini-3.5-flash-lite`) remains a scoped Chat/Responses pilot. The native model dialog showed ten selected accounts. Earlier public pilot streams completed in both protocols. The November 20 private P5 Chat smoke used its dedicated single-seat credential and completed on Playground. That result covers one seat.
- **Flash-Lite 3.1** (`free/gemini-3.1-flash-lite`) remains a separate scoped Chat/Responses pilot. The native dialog showed seven selected accounts. Historical public pilot streams completed in both protocols. Its exact public catalog passed in this run.
- **Lite fallback** (`free/gemini-lite-safe-fallback`) is a virtual pilot alias. The scoped key lists it, and the live public Chat and Responses gates return 422. Deployed-stage fixtures verified bounded pre-stream switching and model reporting, cancellation without replay, and rejection of required tools and tool-result continuation on the text-only chain. Both live routers had zero Combo rows.
- **Argon** (`gemini-4-argon`) was visible in the native catalog with three selected accounts. **Hydrogen** (`gemini-4-hydrogen`) was visible with automatic selection from all eligible accounts. Both stay outside the approved gateway generation scope. Their native catalog entries and prior execution evidence do not establish gateway protocol, account or billing acceptance.
- **Native aliases and protocols.** The GUI confirmed `cursor-combo-vps` maps to `gemini-3.8-flash` and `cursor-coding-combo-vps` maps to `gemini-4-argon`. Public Gemini discovery with the authorized canary returned only Flash and advertised no generation methods. Public Anthropic/Gemini inference and token counting remained closed. Private pilot smoke and isolated SDK tool forwarding remain the evidence for those paths. Image, audio and Live wait for approved demand and contract acceptance.

Google billing coverage across the scheduler's eligible accounts remains **UNKNOWN**. The current Google Projects view covered only its signed-in context. The prior single-seat no-billing evidence and the current Playground configuration establish narrower facts. Cursor's account-specific native BYOK treatment remains **UNKNOWN**. See the [execution tracker](../EXECUTION_TRACKER.md).

## Fresh official v0.3.12 evidence, 2026-11-19

- `gemini-3.8-flash` is approved for production under `free/gemini-3.8-flash`. The native dashboard offered it to ten Ready seats with no explicit model binding. Seven distinct accounts served successful bounded Playground requests in the fresh ledger snapshot.
- `gemini-3.5-flash-lite` is approved only for `free-first-pilot-lite` under `free/gemini-3.5-flash-lite`. Seven Free seats were in the real-model scope. Six distinct accounts served successful Playground requests in the snapshot.
- `gemini-3.1-flash-lite` and `gemini-3.6-flash` were catalog-visible without a specific scope. Argon had a three-account scope, and Hydrogen was alias-mapped without a specific scope. Their fresh execution and billing gates remain open for clean-gateway expansion.
- Both approved models completed direct and public Chat and Responses streams and public Chat tool round trips. Flash had a long-tail Chat sample and an initial Responses timeout. See the [v10 execution checkpoint](master-plan-v10-execution.md) for timings, cancellation and scope evidence.

## Independent candidate inventory, 2026-11-19

The official dashboard reported eight Ready accounts, six Free and two Pro, out of ten records. All five additional candidates appeared in all ten account catalogs. The access modes and Ready counts below describe native scheduler eligibility, subject to successful provider execution.

- `gemini-3.1-flash-lite` and `gemini-4-hydrogen` had no real-model scope or catalog tier restriction in this snapshot. The eight Ready seats were eligible on that basis.
- `gemini-3.6-flash` and `gemini-4-neon` were marked paid with access modes `[1,3]`. Tagged native eligibility requires Pro or Ultra for that combination, leaving two Ready Pro seats.
- `gemini-4-argon` had the same paid restriction and an explicit three-account scope. Two scoped Pro seats were Ready. [AIStudio2API account eligibility](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/aistudio/accounts.go) · [Tier mapping](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/aistudio/benefit.go)

All five advertised Playground `generateContent`, `countTokens`, `batchGenerateContent`, function declarations and 1,048,576 input tokens. Output caps were 65,536 except Argon at 32,768. Neon and Hydrogen advertised an extra-high thinking setting, whereas the two Flash candidates included minimal thinking. The native catalog describes capabilities. Per-candidate streaming, client protocol translation, tools on live traffic and provider billing remain **UNKNOWN**.

**BLOCKED.** None of these five candidates had a successful generation in the fresh native ledger. The most useful initial candidate for an approved bounded trial is 3.1 Flash-Lite, given its catalog tier and lower-complexity use case. Require explicit isolated entitlement/cost evidence, a credential scope and live acceptance before staging it. The existing Flash and Lite aliases retain their established scopes.

## Historical Phase 4 snapshot

The tables below predate the fresh official release. Account identifiers are omitted.

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
