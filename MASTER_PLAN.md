# Free-First AI Infrastructure — Master Plan v10

**Status:** Proposed new authoritative architecture and execution plan (documentation-only; not an implementation claim)  
**Prepared:** 2026-11-19  
**Repository:** https://github.com/nimazasinich/free-first-ai-infrastructure  
**Supersedes:** \`MASTER_PLAN_V9_AUTONOMOUS_EXECUTION.md\` when accepted and merged  
**Audience:** Owner, implementation agents, reviewers, operators

> **Primary objective:** Operate a reusable, secure, quota-aware, multi-model API platform for authorized applications, using verified eligible capacity without unintended metered API charges. Cursor is one client, not the architecture's purpose. Availability must be maximized within real entitlement and provider limits; it cannot be guaranteed without unlimited capacity.

## 0. Decision hierarchy and evidence rules

1. The owner's newest explicit decisions take precedence over older instructions in the repository. In particular, the clean official AIStudio2API v0.3.12 installation is now the baseline; do not restore removed historical source, databases, UI modifications, or support services.
2. This plan defines intended architecture and acceptance gates. \`EXECUTION_TRACKER.md\` defines observed results. The runbook defines operational procedure. A plan statement never substitutes for a successful live test.
3. Official documentation for the **deployed version** outranks assumptions about a later release. Inspect the running 9Router image, AIStudio2API settings, and active clients before changes.
4. Every critical statement is tagged or understood as **VERIFIED**, **HISTORICAL VERIFIED**, **OWNER-REPORTED**, **PLANNED**, **BLOCKED**, or **UNKNOWN**. Do not convert a visible catalog entry into account eligibility, execution capability, or billing proof.
5. No deployment, account/session modification, key expansion, legacy retirement, purchase, or new usage-based provider is authorized by this *document rewrite*. Implementation requires its own gated execution.

## 1. Scope and objectives

### Primary goals

- Maintain one stable, securely authenticated API origin for approved future apps, agents, IDE tools, and programmatic clients.
- Support **verified** OpenAI-compatible Chat Completions and Responses first; expand Anthropic/Gemini and specialized protocols only with contract-preserving adapters and tests.
- Route every permitted request to a model and account actually eligible for the requested protocol, modality, tools, and limits.
- Let AIStudio2API manage its own Google accounts, live eligibility, WAA, quota failures, cooldowns, worker capacity, and same-model account switching.
- Let the central gateway own client identity, model exposure, scoped credentials, tenancy, public policy, and—when truly compatible—cross-model routing.
- Prevent accidental use of Google Developer API, Vertex AI, any metered provider, and unapproved model substitutions.
- Minimize avoidable latency and silent retries while retaining incremental streaming, cancellation, and tool-result continuation.
- Preserve production consumers and unrelated VPS workloads; retire legacy platforms only after consumer replacement is proven.
- Keep operating and architectural knowledge auditable, current, and free of account secrets.

### Explicit non-goals

- Unlimited tokens, unlimited quotas, artificial account creation, or bypassing Google restrictions.
- Treating all 92 historical catalog entries as usable or free.
- Automatic Flash → Flash-Lite downgrade for existing production callers.
- Turning on Fusion, cross-provider billing, or unrestricted 9Router Combo generation.
- Modifying the official AIStudio2API source, UI files, compiled binary, sessions, or application database to implement routing policy.
- Repeating an isolated Cursor native-profile/model-picker test: **owner deferred this workflow**. Existing working MCP and Codex integrations remain the supported client paths.
- Removing OmniRoute, Redis, or legacy candidate merely because they consume RAM.
- Background quota hammering, bulk warmup, hedged requests that double provider usage, or treating a router cost field as a real invoice.

## 2. Deployment baseline and evidence freshness

The following is a **dated snapshot**, not an ongoing guarantee. Reconfirm status at each execution gate.

| Item | Verified / reported baseline (2026-11-19) | Evidence status |
| --- | --- | --- |
| VPS | \`srv4503740909\`, AlmaLinux 9.8, public IP \`185.221.237.84\`, approximately 2 vCPU / 3.6 GiB RAM | Historical verified |
| Workstation | \`DESKTOP-D5I8IQ2\`, Windows 10 Enterprise N build 19045 | Historical verified |
| GitHub | \`main\` at \`a59dc299a691f6f92c2f254bf3abe29f4f61123a\`, Phase 4 PR #6 merged | Verified by repository read |
| Native upstream | **Official AIStudio2API v0.3.12**, \`aistudio2api.service\`, executable under \`/opt/services/aistudio2api/releases/fresh-official-v0.3.12-20261119/\` | Historical verified after fresh install |
| Native runtime | \`/var/lib/aistudio2api-fresh\`, with 10 migrated account records and regenerated model/runtime records | Historical verified; account ability to execute still must be checked |
| Native health | \`http://127.0.0.1:2048/health\` returned 200 after restart | Historical verified |
| Native public host | \`https://aistudio.185-221-237-84.sslip.io/\` returned 200 | Historical verified; this is a separate security surface |
| Clean gateway | \`/opt/9router-clean\`, container \`9router-clean\`, 9Router v0.5.119 as previously pinned | Historical verified; reconfirm current digest |
| Gateway ingress | \`https://r9.185-221-237-84.sslip.io/v1\` | Historical verified |
| Gateway policy | One approved private AIStudio2API provider, four active restricted keys, **zero** combos | Reverified after AIStudio2API reinstall |
| Approved production route | \`free/gemini-3.8-flash\` for Canary, Windows Cursor MCP, and Windows Codex | Reverified policy, not a post-reinstall live generation |
| Approved pilot route | \`free/gemini-3.5-flash-lite\` for \`free-first-pilot-lite\` only | Reverified policy, not a post-reinstall live generation |
| Native catalog | 92 identifiers before fresh reinstall; fresh count must be rechecked | Historical verified, now potentially stale |
| Account counts | 10 records (historically 7 Free-scoped / 3 Pro-scoped) | Records verified; present entitlement / restriction needs fresh observation |
| Account restrictions | Two accounts were previously restricted; owner reports recognition after clean install | Owner-reported; execution and verification status not yet established |
| Disk | About 29 GiB free / 48% used following clean reinstall | Historical verified |
| Latency incident | One ~389-second first-content sample on the production Flash path | Historical verified; root cause **UNKNOWN** |
| Model-to-model failover | Not enabled; zero 9Router combos | Verified in router SQLite |
| Legacy stacks | OmniRoute/Redis and 9Router candidate still have unresolved dependencies | Historical verified; retirement **BLOCKED** |
| Real provider billing | Google invoice/project state not directly verified | **UNKNOWN** |

**Important reset of evidence:** The November 19 fresh AIStudio2API deployment removed old native request ledgers and monitoring. Historical Phase 4 live tests remain valid as historical tests of the old runtime; they do not prove fresh-install model execution. The GitHub runbook and tracker currently contain obsolete paths, PIDs and recovery instructions. Update their *as-built* sections in a separate documentation-only change before any automated deployment follows them.

## 3. Target architecture and trust boundaries

\`\`\`mermaid
flowchart TD
  subgraph clients["Authorized clients"]
    CUR[Cursor MCP]
    COD[Codex scoped launcher]
    APP[Other approved applications]
  end
  subgraph edge["Public edge / policy boundary"]
    TLS[Caddy TLS]
    GUARD[Edge Guard]
    ROUTER[Clean official 9Router]
  end
  subgraph transport["Private upstream transport"]
    PRIVATE[Private host / Docker bridge]
    BRIDGE[Authenticated SSE bridge]
  end
  subgraph native["Google account and model execution"]
    STUDIO[Official AIStudio2API v0.3.12]
    ACC[10 account records / runtime eligibility]
    GOOGLE[Google AI Studio Playground]
  end
  CUR --> TLS
  COD --> TLS
  APP --> TLS
  TLS --> GUARD --> ROUTER --> PRIVATE --> BRIDGE --> STUDIO
  STUDIO --> ACC --> GOOGLE
  LEGACY[OmniRoute / candidate: separate legacy consumers] -. never silently merged .- ROUTER
\`\`\`

**Security boundaries:**

- **Client/public boundary:** TLS termination, request limits, client authentication, key-specific model allowlists, and audit metadata; no privileged upstream token is exposed.
- **Router/private boundary:** 9Router has exactly the approved upstream connection. Dedicated bridge-network egress restrictions prevent arbitrary internet access or unrelated provider calls.
- **Bridge/native boundary:** The bridge validates the upstream bearer, endpoint, request schema and permitted native model ID; pass through real SSE incrementally. The native token is not returned to clients.
- **Native/Google boundary:** Official AIStudio2API authenticates and schedules existing Google accounts; only the authorized Playground generation path may be selected.
- **Parallel native public host:** The existing AIStudio2API public API and dashboard bypass 9Router's client-level allowlists. Keep explicit native authentication and administrative controls. Inventory real users of that host before tightening access; never pretend the 9Router allowlist protects this independent path.
- **Legacy boundary:** OmniRoute, its Redis/webhook/cron and the old candidate are separate, currently necessary systems. No data, tokens, model access, or billing paths transfer into the clean gateway implicitly.

## 4. Responsibility matrix — one owner per concern

| Concern | Primary owner | Do **not** duplicate elsewhere |
| --- | --- | --- |
| Google account login/session lifecycle | Official AIStudio2API | No gateway cookie import or session re-login automation |
| Real \`ListModels\`, tiers, per-account model capability | AIStudio2API | No invented gateway entitlement engine |
| WAA proof, worker acquisition, worker concurrency | AIStudio2API | No parallel custom account pool in Bridge |
| Same-model account selection, retries, cooldown | AIStudio2API | No second account retry loop in 9Router |
| Upstream model aliases | AIStudio2API \`MODEL_MAPPING\` for native clients; 9Router explicit catalog for public aliases | Avoid alias-on-alias ambiguity |
| Per-model account preference | AIStudio2API \`MODEL_ACCOUNTS\` on **real model IDs** | Never use it as client key authorization |
| Per-native-key account restriction | AIStudio2API \`API_KEY_ACCOUNTS\`, when needed | Not the 9Router model ACL |
| Public client credentials and permitted model IDs | 9Router, Edge Guard, Bridge defense-in-depth | Do not infer from native catalog visibility |
| Model-to-model candidate failover | 9Router only after exact capability and failure semantics are proven | Never hide a downgrade from an unconsenting caller |
| Public TLS, host routing, edge guard | Caddy + existing Edge Guard | No extra internet-facing daemon by default |
| Endpoint adaptation, limited SSE plumbing | Private bridge | No account scheduler or complete second proxy product |
| Public usage/audit policy | Router + edge metadata | Never log account cookies / prompt bodies by default |
| Root-cause tracing | Correlated edge/router/bridge/native events | No blind p95 inference from one request |
| Billing-safety evidence | Route inventory + native effective channel + independent provider billing check | A router \`cost\` field is not a provider invoice |
| Client migration / retirement proof | Client-specific test suite and legacy dependency register | No bulk rewrite of 95 saved Codex profiles |

## 5. Official AIStudio2API configuration: required interpretation

The authoritative baseline is [AIStudio2API v0.3.12 README](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/README_en.md) and [development reference](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/docs/development.md), plus the release-tagged code.

### \`MODEL_MAPPING\` — pure alias translation

Format: \`alias:actual-model-id\`, comma-separated; split at the final colon.

The currently migrated configuration was inspected with **seven** mappings, including:

- \`cursor-argon-vps\` → \`gemini-4-argon\`
- \`cursor-coder-vps\` → \`gemini-4-hydrogen\`
- \`cursor-flash3.5-vps\` and \`cursor-free-vps\` → \`gemini-3.5-flash-lite\`
- \`cursor-flash3.8-vps\` and \`cursor-combo-vps\` → \`gemini-3.8-flash\`
- \`cursor-coding-combo-vps\` → \`gemini-4-argon\`

**Consequence:** The two \`combo\` names here **do not** represent fallback chains. Do not rename or remove them until their real consumers are identified. New aliases must describe actual behavior. Public 9Router aliases must have their own scoped ACL and accepted upstream ID.

### \`MODEL_ACCOUNTS\` — model-specific automatic account scope

Format: \`actual-model-id:account-id|account-id\`, comma-separated; restricts the automatic candidate set and intersects with applicable native-key account scope. The release-tagged code checks the effective real model ID in \`ScopedSelection\`.

- The inspected fresh configuration had **five** rules. Real \`gemini-4-argon\` referenced three existing account IDs; real \`gemini-3.5-flash-lite\` referenced seven. The additional rules using \`cursor-argon-vps\`, \`cursor-free-vps\`, or \`cursor-flash3.5-vps\` should be treated as potentially redundant/ineffective for ordinary mapped generation, pending UI/API verification.
- Unlisted models do **not** become forbidden; the upstream still considers all *eligible* accounts subject to its other restrictions.
- Explicit account binding or resource/session affinity can change automatic selection semantics.
- A scope entry is not proof of **live entitlement**, **billing status**, **model capability**, or successful account execution.
- Any later correction must be done using the app's **official Settings/Model catalog UI**, not direct edits to its internal databases, patched binary, source, or custom UI.

### Other important settings

- \`UPSTREAM_CHANNELS\`: official v0.3.12 **default is \`playground\`**. The new \`.env\` does not explicitly set it. That is not, by itself, a misconfiguration; validate effective channel via Settings and bounded runtime evidence. Do not enable legacy Build as an assumed backup.
- \`ROUTING_STRATEGY\`: default \`round-robin\`, selecting among **accounts** for the same model. \`fill-first\` is a separate preference, not cross-model fallback.
- \`MAX_ACCOUNT_SWITCHES\`: default 3 for non-quota failures. Quota-limit failures have separate handling; do not replicate all retries at the gateway.
- \`FIRST_EVENT_HEDGE\`: default \`off\`. Enabling it can issue an extra provider request and consume quota; do not turn it on to mask slow requests without measured benefit and an authorized quota budget.
- \`API_KEY_ACCOUNTS\`: a native key-to-account rule. It is **not** a model allowlist.
- \`MODEL_CHANNELS\`: a per-real-model channel preference. Leave unset unless needed for a proven approved route.
- \`WAA_BACKEND\`: current environment specifies \`spidermonkey\`; preserve official behavior and test actual runtime health.
- \`REQUEST_TIMEOUT\`: official default 30 minutes for a request/continuation round; this does not justify arbitrary 30-minute intermediary waits.
- \`FAKE_STREAM\`: defaults false; preserve actual incremental streaming.
- Account-level login/verification restrictions imposed by Google may persist through fresh installs. Do not bypass provider account verification with hidden browser/session workarounds.

**Source-code semantics:** [\`internal/aistudio/channel.go\`](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/aistudio/channel.go) intersects key and model candidate scopes for automatic selection; [\`internal/app/runtime.go\`](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/app/runtime.go) resolves aliases before actual generation and schedules via the account pool.

## 6. Model governance: five independent states

For every model and account, distinguish:

1. **CATALOG_VISIBLE** — the identifier appears in a native authenticated catalog.
2. **ACCOUNT_ELIGIBLE** — live account entitlement, method, modality and channel checks pass.
3. **EXECUTION_VERIFIED** — a bounded request actually completed on the approved channel; evidence identifies timing and selected account anonymously.
4. **GATEWAY_PILOT_ENABLED** — the model is available only to a dedicated scoped test key.
5. **PRODUCTION_ENABLED** — explicitly authorized for named production keys after capability, reliability and billing gates.

Other valid states: \`COOLDOWN\`, \`ACCOUNT_RESTRICTED\`, \`BILLING_UNVERIFIED\`, \`PROTOCOL_UNSUPPORTED\`, \`BLOCKED\`, \`NOT_RUN\`.

Each approved catalog record should include:

\`upstream_id\`, \`public_alias\`, \`source_version\`, \`account_scope_count\`, \`channel\`, \`protocols\`, \`streaming\`, \`tools\`, \`json\`, \`modalities\`, \`reasoning_level\`, \`input_limit\`, \`output_limit\`, \`billing_evidence\`, \`latency_sample\`, \`last_verified_at\`, \`owner_key_scope\`, and \`rollout_stage\`.

Never publish actual account names, session cookies, fingerprints, passwords, native bearer tokens, or the contents of \`auth/\`.

### Current model decisions

| Model / route | Current role | Next gate |
| --- | --- | --- |
| \`free/gemini-3.8-flash\` → \`gemini-3.8-flash\` | Existing production route | Post-reinstall bounded Chat/Responses and tool regression |
| \`free/gemini-3.5-flash-lite\` → \`gemini-3.5-flash-lite\` | Restricted pilot only | Post-reinstall entitlement, channel and pilot generation check |
| \`gemini-3.1-flash-lite\`, \`gemini-3.6-flash\` | Candidates, not approved | Real scope, capability, billing and bounded execution |
| \`gemini-4-argon\`, \`gemini-4-hydrogen\` | Native candidate/subscription routes, disabled in clean gateway | Subscription authorization and no-extra-metered-charge evidence; do not silently promote |
| Image, TTS, Live, transcription, search, tools, other variants | Protocol-specific roadmap | End-to-end compatible adapter and permission proof |

Changing from one model to a lower-capability model is not ordinary service failover. It requires explicit caller opt-in and a contract that the fallback truly meets the request's needs.

## 7. Routing and failover policy

### Tier A — same-model account failover (already owned by AIStudio2API)

An unbound request is classified by account eligibility, live method, available worker, concurrency, and cooldown. AIStudio2API may switch to another eligible account before its first semantic upstream event, with documented rules for retryable errors and capacity. Maintain a single native request so this layer can do its work.

### Tier B — transport failure and bridge policy (already deployed)

The private bridge currently:

- Authenticates the single native upstream credential.
- Allows exactly \`gemini-3.8-flash\` and \`gemini-3.5-flash-lite\` on \`/v1/chat/completions\` and \`/v1/responses\`.
- Proxies \`/v1/models\` with a filtered catalog.
- Preserves real SSE and \`Retry-After\`.
- Maps selected native HTTP \`502/503/504\` responses to **terminal 500** to avoid repeated stock-9Router upstream sends.

This is an intentional safety workaround, **not** proof that all retries are optimal. It also means a naïve 9Router Fallback combo expecting 502/503/504 may **not** activate as documented. Never add a model combo without an isolated end-to-end failure-injection test of the bridge's actual responses. Changing bridge semantics must not create retry storms or duplicate non-idempotent calls.

### Tier C — model-to-model failover (planned, not enabled)

Permit only with all of the following:

1. A separate **opt-in** alias/key, not existing production credentials.
2. The model pair is separately verified through current native Playground access, and a billing-safe route exists for each.
3. Capabilities are compatible for this exact request: text, reasoning requirements, tools, tool-result continuation, response format, context, output size, and modality.
4. Fallback is allowed only **before** first content/tool event; no automatic replay after client-visible stream starts.
5. Only documented, tested transient conditions trigger fallback; never 400/401/403, unknown model, invalid tool schema, or an expired explicit-account session.
6. The route is bounded: at most a verified finite attempt policy, respects \`Retry-After\` and cooldown, and surfaces a clear terminal error on exhaustion.
7. The selected actual model is observable without exposing private account identity.
8. Real quota-burning error tests are replaced with synthetic fixtures. No deliberate 429 exhaustion.

**Go/no-go:** \`9Router → Flash → Lite\` is **BLOCKED for broad production** because the secondary may downgrade capability. A fully isolated *text-only* opt-in experiment may be evaluated if policy, bridge behavior, and the deployed router version genuinely support it. Combo count stays zero until promotion gates pass.

### Tier D — optional advanced routing (not currently authorized)

- **Round robin across models:** disabled; it ignores task compatibility.
- **Fusion / parallel multi-model:** disabled; multiplies quota use.
- **Smart Router / model-based classifier:** disabled unless approved and budgeted; classification itself creates additional requests.
- **Paid or metered emergency fallback:** prohibited.
- **Hedge / parallel first-event request:** disabled unless owner explicitly approves measured quota tradeoff.

## 8. Unified protocol/API roadmap

The **current public contract is deliberately narrow**, not a complete universal proxy.

| External feature | Current state | Target condition |
| --- | --- | --- |
| OpenAI \`GET /v1/models\` | Working for scoped models | Preserve filtered catalog per credential |
| OpenAI Chat Completions | Working / previously tested | Reverify post-reinstall SSE, tools and cancellation |
| OpenAI Responses | Working / previously tested | Reverify post-reinstall basic and structured continuation |
| Anthropic Messages | Not supplied by existing bridge | Add only with tested request/response/tool/SSE mapping or an officially supported direct provider path |
| Gemini native API shape | Not supplied by existing bridge | Add a separate authenticated adapter only if compatible and authorized |
| Image generation / media | Not in current bridge allowlist | Explicit protocol and modality route, scoped key, exact evidence |
| TTS, audio, Live WebSockets | Not in current bridge allowlist | Distinct validated transports; do not fake coverage by advertising catalog models |
| Background/long-running operations | Not in current bridge allowlist | Design durable task ownership before exposure |

For each protocol, test \`request validation → model authorization → payload adapter → provider execution → streaming framing → error semantics → client tool continuation\`. Preserve provider-specific features only when adapter mapping is demonstrably lossless enough for the intended client.

Prefer expanding 9Router's supported native mechanisms rather than writing an unrestricted multiprotocol proxy. The private bridge should remain small and auditable.

## 9. Security, secrets, and no-unintended-charge controls

**Hard rules**

- One explicitly approved Playground-bound native upstream for the Free-First gateway, no metered Google Developer/Vertex secrets, no hidden other providers, no permissive fallback.
- Keep 9Router container outbound traffic constrained to its intended private route. Preserve network-isolation tests and host firewall/egress policies.
- Per-client scoped keys expose **only** permitted public model IDs. Bridge independently rejects all other native IDs before forwarding.
- The public native AIStudio2API hostname remains an **independent auth surface**, requiring separate ACL, admin login, TLS and access review.
- Never log raw credentials, cookies, entire account configuration, Google verification content, or sensitive prompts in public logs or Git.
- Use Windows DPAPI for local client key storage where implemented; do not tamper with existing Cursor native BYOK settings.
- Handle rate limits and Google service restrictions as real upstream boundaries. No automated evasion, unapproved identity rotation or provider billing circumvention.

**Billing policy**

- \`NO_METERED_PATH_CONFIGURED\` is checkable from actual upstream and egress inventory.
- \`PROVIDER_INVOICE_CHECKED\` requires an authorized billing source; absent that, mark **UNKNOWN**.
- Subscription entitlement does not automatically prove third-party/API usage is included or that any model is unlimited.
- Router \`cost\` fields are application accounting, not bank/provider charges.
- A newly discovered model enters **BILLING_UNVERIFIED** until the relevant mode of use is documented and validated.
- No purchase, card attachment, billing toggle, Developer API, or paid fallback is part of this plan.

**Recovery preference:** The owner requested no new backups during the AIStudio2API clean installation. Do not recreate deleted AIStudio2API session backups, restore old runtime data, or export account tokens. For gateway/legacy changes, use reviewed Git revisions, isolated test environments, small reversible changes and explicit authorization if a persistent snapshot of sensitive state is necessary. If a safe change cannot be made without recovery provisions the owner declines, keep that change blocked.

## 10. Latency, correctness, and observability

### Incident to resolve

One historical production Flash sample reported approximately **389 seconds to first content**. A bridge socket timeout of 115 seconds does not establish a 115-second total request deadline; multiple phases and socket reads may be involved. Do not assign root cause without reconstructing actual timings.

### Measurement model

Log correlated **redacted** request metadata, with UTC time and monotonic durations:

\`client_received\` → \`edge_accepted\` → \`router_selected\` → \`bridge_forwarded\` → \`native_request_start\` → \`native_account_selected\` → \`upstream_headers\` → \`first_sse_event\` → \`first_semantic_content\` → \`completed_or_cancelled\`.

Report exact protocol, streaming flag, actual model, attempt count, response code, cooldown status and selected phase timings—never email/session material.

- Compare direct and gateway measurements **only as independent samples**; avoid treating unrelated generations as a controlled A/B experiment.
- Report median, maximum and sample size; only calculate p95 for a defensible sample size, and label it descriptive rather than a guarantee.
- Separate provider/account scarcity from bridge/Caddy/router processing latency.
- Confirm streaming is incremental: tool-call deltas and content chunks arrive before upstream completion, without full-body buffering.
- Verify client cancellation releases upstream resources; no silent duplicate generation, hanging worker or retry storm.
- Never "fix" delay by merely raising intermediary timeouts indefinitely.
- Limit live probes; run failure, 429, 503, disconnect, delayed header and partial-stream tests against local fixtures.

**Targets:** No fixed universal TTFT SLA is asserted without a measured stable baseline. A passing improvement must show statistically defensible or repeatable removal of **avoidable gateway overhead** without regression in tool or streaming correctness.

## 11. Capacity and operations

- VPS has constrained CPU and memory. Measure current RSS, resident workers, memory/swap activity, open FDs, CPU and filesystem before any new daemon.
- Preserve the current SpiderMonkey-based native WAA backend unless official UI and objective tests justify changing it.
- Avoid oversizing \`WARM_WORKER_LIMIT\` and \`MAX_ACTIVE_WORKERS\` solely because 10 accounts exist. Set capacity according to measured concurrent useful workloads and actual RAM headroom, through supported UI.
- Account restriction, cooldown, login and renewal are **status** and entitlement concerns, not reasons to re-import sessions automatically. Use the official login/verification flow when Google requires it.
- Do not reintroduce deleted custom warmup, safety-monitor, account-index-injector or reference services to the new official install.
- Maintain minimal probes for native health, public 401/403 policy, bridge health and client-shape smoke tests. If scheduling is needed, use a small approved external monitor that never injects hidden model calls.
- Avoid per-request verbose body logging; aggregate status/latency metrics and use bounded retention.
- Keep a post-change manifest of deployed binary path/version, router digest, services, listeners, network rules and approved access policy.
- Respect user preference for changes to AIStudio2API **through official GUI only**; no source, UI, direct database or hidden application config rewrites.

## 12. Implementation roadmap and phase gates

These phases replace the older single-pass deployment checklist. They are **dependency gates**, not promises of delivery dates.

### P0 — Reconcile the new baseline (first)

**Purpose:** Stop executing stale runbook assumptions after the 2026-11-19 clean reinstall.

- Reconfirm native official version, live service path, 10 account records, eligibility indicators and selected channel.
- Verify current 9Router digest, four keys, two catalog aliases, one upstream, zero combos, public 401/403 and zero forbidden forwards.
- Identify stale backup references, dead unit names, deleted directories and old PIDs in GitHub docs; update them without restoring old services.
- Compare actual bridge-to-native behavior with the new installation.
- Preserve all client integrations and production keys.

**Exit:** An accurate as-built architecture, fresh nonsecret inventory, no unsafe stale instructions, and policy regression passing. Live generation remains gated until effective Playground and billing path are established.

### P1 — Native configuration audit (read-only → GUI changes only when justified)

**Purpose:** Remove semantic confusion while retaining existing consumers.

- Classify \`MODEL_MAPPING\` aliases as real one-to-one aliases; do not represent them as Combos.
- Verify \`MODEL_ACCOUNTS\` entries against **real** model IDs and actual account eligibility; identify redundant alias-name scopes.
- Verify effective \`UPSTREAM_CHANNELS=playground\` through official Settings/runtime evidence, not merely by inspecting \`.env\`.
- Inspect \`ROUTING_STRATEGY\`, retry limits, WAA worker capacity and first-event hedge state.
- Verify each existing key/account scope through supported UI and independent router/bridge enforcement.
- Propose minimal changes only for proven defects. No renaming of aliases used by existing clients without compatibility plan.

**Exit:** Signed-off semantic map of every alias, source account scope, effective upstream channel and authorized caller. No paid path.

### P2 — Revalidate live model and protocol execution

**Purpose:** Distinguish post-reinstall reality from historical Phase 4 tests.

- Bounded no-cost-path-confirmed native and public Chat/Responses probes on Flash and Lite.
- Reconfirm actual selected channel, response model, stream events, tools and tool-result continuation where claimed.
- Validate restricted-key catalog, authorization denials and zero forbidden upstream forwards.
- Recreate a nonsecret eligibility/capability matrix with fresh timestamps, without restoring deleted request history.

**Exit:** Fresh proof of permitted route execution, or a precise **BLOCKED** record without mislabeling historical tests as current.

### P3 — Latency and retry root-cause engineering

**Purpose:** Explain the historical long first-content delay and remove avoidable local overhead.

- Reconstruct event phases and retry patterns from available logs; instrument sanitized timings where needed.
- Verify bridge status translation versus deployed 9Router retry semantics; no uncontrolled retry loops.
- Test 429/Retry-After, 502/503/504, upstream silence, client cancellation, partial SSE and tool completion in isolated fixtures.
- Fix only reproducible faults in clean gateway/bridge; do not modify native AIStudio2API source.

**Exit:** Before/after evidence for a real fix or an evidence-backed conclusion that the delay is upstream/provider/account-driven or unreplicated.

### P4 — Capability-based additional model pilots

**Purpose:** Expand only to models genuinely valuable for the API platform.

- Score candidates by entitlement, permitted channel, task capabilities, reliability, latency and verified no-metered-path evidence.
- Keep Flash production and Lite pilot stable while evaluating additional candidates.
- Stage each model behind a **new restricted pilot key**, then test via limited Chat/Responses and relevant tools.
- Leave Argon/Hydrogen gateway-disabled unless subscription/billing and access gates clear; no presumption that a Pro label grants unlimited Argon.

**Exit:** At least one independently verified useful additional model **or** a documented no-go. No forced expansion.

### P5 — Explicit opt-in, capability-compatible fallback

**Purpose:** Add model-level resilience **only** when semantically safe.

- Inspect installed 9Router Combo/fallback handling and bridge terminal-status behavior under fixtures.
- Prefer models of equivalent required capability; do not auto-downgrade a required reasoning, tools, multimodal, or JSON workflow.
- Trial a dedicated text-only opt-in route with finite attempts, true model reporting and failure-injection tests; no production key expansion.
- Leave 9Router Combo count at zero if no compatible pair or safe hook is proven.

**Exit:** Tested isolated fallback plus authorization boundary **or** precise reproducible blocker; broad production remains unchanged without approval.

### P6 — Selective protocol expansion

**Purpose:** Become a genuinely reusable API platform beyond two OpenAI-compatible routes.

- Prioritize client demand and protocol maturity; do not promise Anthropic/Gemini/media semantics solely from native catalog entries.
- Implement narrow adapters only when request validation, errors, SSE, tools, multipart/websocket/streaming and cancellation are testable.
- Separate security and quota policies by modality and endpoint family.

**Exit:** One newly supported protocol/mode with full acceptance evidence and independently scoped credentials, not superficial endpoint advertising.

### P7 — Client onboarding and operational maturity

**Purpose:** Make the clean gateway reliably usable by future applications without modifying native Cursor settings.

- Retain working Cursor MCP, Codex scoped launcher and DPAPI storage. Keep native Cursor model-picker work **deferred**.
- Build a repeatable, scoped onboarding contract: endpoint, key scope, exact models, tools/stream support, limits, test fixture and revocation.
- Implement small health/status reporting, post-change regression and secret hygiene; avoid duplicative services on the constrained VPS.

**Exit:** A second independent non-IDE application/client can use an approved route correctly, with zero access to unapproved models.

### P8 — Legacy reduction and retirement (last, still blocked)

**Purpose:** Remove old OmniRoute/candidate/Redis resources without breaking real consumers.

- Inventory all active Cursor MCP registrations, Codex saved profiles, Caddy routes, webhook, cron, old dashboard/API consumers and current usage.
- Classify \`ACTIVE_REQUIRED\`, \`ACTIVE_REPLACEABLE\`, \`CONFIGURED_BUT_UNUSED\`, \`OBSOLETE_VERIFIED\`, and \`UNKNOWN\`.
- Migrate only exact capability matches with a real application test. The 95 saved OmniRoute Codex profiles are **not** 95 confirmed live callers, and should not be mass-converted.
- Keep legacy infrastructure running while any active consumer or management function lacks a verified replacement.
- Remove exclusive resources only after replacement/obsolescence and a safe, authorized reversible stop are proven.

**Exit:** Each retired component has no unresolved consumers, the new API and unrelated VPN/monitoring still pass, and no data/credential exposure occurred. If not, status remains **BLOCKED**.

## 13. Verification standards and release contract

Each gate must attach a reproducible, nonsecret evidence record with:

- Exact component versions/digests, current time in UTC, relevant service state and applicable test fixture.
- Test class: **LIVE**, **SYNTHETIC**, **READ_ONLY**, or **HISTORICAL**.
- Test result: \`PASS\`, \`FAIL\`, \`PARTIAL\`, \`BLOCKED\`, \`NOT_RUN\`, \`UNKNOWN\`.
- Requested model, **actual** model, protocol, endpoint, restricted key name (not value), response status, first header/event/content timings if relevant.
- Upstream-forward count for rejected requests, failure/retry attempt counts and whether streaming had already begun.
- Account eligibility summarized without identifier leakage; actual invoice status never guessed.
- Baseline versus new behavior; exact changed paths and rollback/stop condition.

### Production promotion gates (all required)

- **Compatibility:** Exact route, model, protocol and required capabilities pass real and fixture tests.
- **Authentication:** Missing/invalid token 401; forbidden model 403; unsupported route 404/405; zero forbidden native forwards.
- **Network:** Dedicated container egress still denies unrelated destinations.
- **Billing:** No extra metered provider path or fallback; unresolved invoice status explicitly reported.
- **Retry/cooldown:** No duplicate upstream execution or infinite retry.
- **Streaming:** Data and tool deltas remain incremental; late stream failure is not silently replayed.
- **Isolation:** Old keys and clients are unchanged unless explicitly in approved promotion scope.
- **Recovery:** Exact rollback can be executed without resurrecting deleted native state or violating the owner's no-new-AIStudio-backup preference.
- **Documentation:** Tracker, model matrix and runbook match actual live state before marking PASS.

If any required evidence is missing, keep candidate isolated or disable it. Never broaden production to make a demo appear successful.

## 14. Repository and implementation deliverables

**Canonical documents**

- This plan: \`MASTER_PLAN.md\` (the architecture and gates; must be updated when owner decisions change).
- \`OWNER_FINAL_DECISIONS.md\`: owner authorization and constraints; if contradictory, reconcile explicitly rather than silently changing policies.
- \`EXECUTION_TRACKER.md\`: append-only, time-stamped observation log.
- \`docs/runbook.md\`: only actionable, **current** deployment and recovery paths.
- \`docs/model-eligibility-matrix.md\`: model/account/protocol/channel/billing evidence.
- \`docs/client-migration.md\`: clients, access scope, constraints, results.
- \`docs/legacy-retirement.md\`: dependency classification and blocking consumers.
- Proposed \`docs/architecture-contract.md\`: endpoint ownership, request path, protocol support and auth/trust boundary matrix (only if the plan alone becomes unwieldy).
- Proposed \`docs/latency-evidence.md\`: timestamped request correlation and incident outcome (only when measurements exist).

**Change discipline**

- Small doc-only PR for this rewritten canonical plan; **no production deploy** in the plan PR.
- Further branches/PRs per execution phase. Validate tests and live scope before merging implementation changes.
- Never push secrets, login material, raw session records, sensitive logs or restored historical AIStudio2API data.
- Avoid duplicate or conflicting master plans. Preserve the v9 file only as a clearly superseded historical reference.
- Any stale GitHub evidence after the clean reinstall is marked historical until reverified.

## 15. Immediate next action

**Start with P0, not with a new model Combo.**

1. Revalidate the live post-reinstall upstream + gateway and effective official Playground channel.
2. Fix stale paths and backup instructions in documentation **without restoring old AIStudio2API installations**.
3. Confirm four restricted keys, two approved public models, one upstream and zero Combo routes.
4. Run only the minimum live Flash/Lite tests justified by verified billing route and current account entitlement.
5. Then perform P1 model mapping/account scope audit and P3 latency work in that order.
6. Consider P4/P5 expansion only after the preceding gates prove stable and do not silently downgrade capabilities.

**Definition of success:** The project exposes an increasingly useful set of verified, contract-compatible models through one controlled client API, with honest quota exhaustion, stable streaming/tools, explicit restrictions, no unforeseen metered paths and no unresolved collateral changes. "Always available" is an optimization objective, **not a promise**.

## Appendix A — Existing key / model boundaries

| Key name | Allowed public model at baseline | Status |
| --- | --- | --- |
| \`canary\` | \`free/gemini-3.8-flash\` | Production |
| \`free-first-windows-cursor\` | \`free/gemini-3.8-flash\` | Production / Cursor MCP |
| \`free-first-windows-codex\` | \`free/gemini-3.8-flash\` | Production / Codex |
| \`free-first-pilot-lite\` | \`free/gemini-3.5-flash-lite\` | Isolated pilot |

Any fifth key, expanded allowlist, or Combo requires a separate change and evidence. Do not publish key values.

## Appendix B — Fundamental distinctions

| Often confused | Correct interpretation |
| --- | --- |
| Visible model / eligible model | Catalog is not entitlement |
| Eligible model / executable model | Entitlement is not a successful request |
| Model alias / model Combo | One-to-one name mapping is not fallback |
| Native \`MODEL_ACCOUNTS\` / public ACL | Account selection is not public authorization |
| Same-model account switch / cross-model failover | Different layers, different correctness obligations |
| \`UPSTREAM_CHANNELS\` absent / unsafe channel | v0.3.12 default is Playground; verify actual effective channel |
| Router accounting cost / Google invoice | Different evidence sources |
| Successful fixture / real execution | Fixture tests prove code path, not upstream availability |
| Active saved profile / active service consumer | A saved config is not proof of traffic |
| One good latency sample / SLA | A sample is not a performance guarantee |
| Fresh install / provider account verification | Clean local state does not override Google restriction |

## Appendix C — Source references and baseline lineage

- [Official AIStudio2API v0.3.12 README](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/README_en.md)
- [Official AIStudio2API v0.3.12 development/configuration](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/docs/development.md)
- [AIStudio2API account-scoped selection code](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/aistudio/channel.go)
- [AIStudio2API mapped-model execution code](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/app/runtime.go)
- [Official 9Router Combo reference](https://github.com/decolua/9router/blob/master/gitbook/content/en/features/combos.md) — examples in that document are illustrative, **not** evidence that a given model is free, available or unlimited.
- [Existing project README](README.md), [execution tracker](EXECUTION_TRACKER.md), [runbook](docs/runbook.md), [model matrix](docs/model-eligibility-matrix.md), [client matrix](docs/client-migration.md), [legacy audit](docs/legacy-retirement.md), [owner decisions](OWNER_FINAL_DECISIONS.md)
- [Phase 4 PR #6](https://github.com/nimazasinich/free-first-ai-infrastructure/pull/6) — merge commit \`a59dc299a691f6f92c2f254bf3abe29f4f61123a\`

---
**Document status:** Proposed. It changes only the plan and associated documentation when merged; it neither reconfigures nor audits the live runtime by itself.
