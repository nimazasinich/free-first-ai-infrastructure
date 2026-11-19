# Official AIStudio2API v0.3.12 GUI audit

Audited on 2026-11-19 in the [production management console](https://aistudio.185-221-237-84.sslip.io/). The existing browser session showed the signed-in administrator, generation service **Running**, and **v0.3.12**, current and up to date. The running binary reported revision `c3c9cbc43b88b4848b3cf1d5b87701bc01135812`. The audit covered every Settings group, the Accounts page and restriction dialogs, all seven relevant model detail dialogs, Logs, Cooldowns & requests, Usage, Access (Connect), and Version.

## PR #12 and production baseline

**PASS.** Reviewed the full diff and current CI at `026b09d090cd115be45717050696cd861482b7db`. The connection checker uses GET only, rejects redirects, and sends the scoped credential only to the canonical origin. The router fixture uses a pinned build, disposable state, synthetic credentials, loopback mocks, and no network. The diff's address-shaped URL is a synthetic test fixture. The protocol and Combo blockers matched the evidence. The 19 Python tests and two Node tests passed locally. GitHub merged [PR #12](https://github.com/nimazasinich/free-first-ai-infrastructure/pull/12) into `main` at `637287bad0b85a54beb51830f2faf26e18458408`. The audit branch starts at that merge.

## Before and after configuration matrix

Each “Saved → after reload” entry shows the observed baseline, the post-reload value, and the recommended value when all three match. The active column distinguishes exercised state from a dormant feature or a setting awaiting its normal trigger. Reopened **Settings → Service, Capacity, Runtime & channels, Models & protocols, Network, Security** after browser reload and compared all six groups. Neither restart banner appeared. Read-only VPS checks matched the native process, configuration fingerprint, account set fingerprint and loopback sockets. No applicable environment or CLI override was detected, and no field was classified **BLOCKED — ENVIRONMENT OVERRIDE**. The defaults and save effects come from the tagged implementation. [Configuration and apply semantics](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/docs/development.md) · [Official Settings controls](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/web/src/components/SettingsPanel.vue)

### Service

| Setting | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| `AUTO_START` | On → On | Service running. Setting is used at management startup | Off | Editable, next management start | Keep automatic recovery when management starts |
| `LISTEN_ADDR` | `127.0.0.1:2048` → same | Confirmed listening on loopback | `127.0.0.1:2048` | Editable, management restart | Preserve the private manager/API listener behind Caddy |
| `PREVIEW_LISTEN_ADDR` | `127.0.0.1:2050` → same | Confirmed listening on loopback | `127.0.0.1:2050` | Editable, management restart | Preserve the separate loopback preview origin |
| `PROXY_API_KEY` | One masked key → same | Unauthenticated native models rejected. Configured key matches the private Bridge credential | Empty | Editable, management restart | Preserve authentication and working Bridge access |
| `API_KEY_ACCOUNTS` | Empty → empty | GUI showed all accounts for the key, subject to model and account eligibility | Empty | Editable, immediate | Preserve the existing native key policy. Public Gateway keys enforce separate model scopes |
| `AISTUDIO_AUTH_STATES` | `auth` → same | Existing auth location in use, ten account records matched | `auth` | Editable, next generation-service start | Preserve account/session discovery |
| `MEDIA_OUTPUT` | Inline data URI → same | Inline references configured | `inline` | Editable, immediate | Keep media in authenticated responses. URL mode serves generated files through `/media`, which has no native API-key check |
| `MEDIA_BASE_URL` | Empty → empty | Dormant in inline mode | Empty | Visible in URL mode, immediate | No media base URL needed |
| `HIDE_DOCK_ICON` | Inapplicable → same | Linux VPS has no Dock | Off | macOS desktop only, immediate there | **BLOCKED — OUTSIDE OFFICIAL GUI** on this host |

The media assessment concerns the native application. Gateway route policy is a separate boundary. [Official media output documentation](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/README_en.md)

### Capacity

| Setting | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| `WARM_WORKER_LIMIT` | 10 → 10 | Warm target 10 | 10 for SpiderMonkey | Editable, immediate | Retain warm capacity. Historical startup completed 10/10 in 21.44 s |
| `MAX_ACTIVE_WORKERS` | 20 → 20 | Worker ceiling 20 | 20 for SpiderMonkey | Editable, immediate | Keep an upper bound on worker scaling. Current Ready accounts reach their eligibility/concurrency limits first |
| `WARM_STARTUP_CONCURRENCY` | 5 → 5 | Dormant under SpiderMonkey | 5 | Capacity control, immediate for applicable backend | Applies to on-demand Camoufox cold starts. Initial prewarm is sequential |
| `PER_ACCOUNT_CONCURRENCY` | 2 → 2 | Two slots per eligible account | 2 | Editable, immediate | Retain the current concurrency budget per seat |
| `ROUTING_STRATEGY` | Round Robin → same | `round-robin` | Round Robin | Editable, immediate | Distribute selection among eligible accounts for the same model |
| `ACCOUNT_ORDER` | Empty → empty | Dormant with Round Robin | Empty | Visible for Fill First with multiple accounts, immediate | Keep implicit ordering. Fill First favors the first available account in saved order, with unlisted accounts following in ID order |
| `MAX_ACCOUNT_SWITCHES` | 3 → 3 | Up to three switches after non-quota upstream errors | 3 | Editable, immediate | Retain bounded switching. Quota errors use native cooldown and remaining-account selection |

The VPS has 2 vCPU and 3,655 MiB RAM. The idle snapshot showed 1,521 MiB available, 1,461 MiB swap occupied, and zero swap-in/out during two sampled intervals. AIStudio2API used about 440 MiB RSS and 25 threads. SpiderMonkey is in-process, so RSS does not isolate worker memory. The clean 9Router used about 72 MiB, OmniRoute 410 MiB, Redis 12 MiB and the legacy candidate 17 MiB. There were zero active requests and zero cooldowns in the GUI at observation. Prior successful prewarming establishes startup behavior for that earlier account state. Current resident worker count, loaded per-worker memory, peak demand, and peak cancellation cost remain **UNKNOWN**.

At two per account the eight Ready seats offer at most 16 simultaneous slots across accounts, with a nominal upper bound of 12 Lite slots and four Argon slots for their respective scopes. Provider quotas, cooldowns, temporary account state and model eligibility can reduce those figures. They are scheduling bounds. There is sufficient idle headroom to keep current settings. Measured savings from shrinking the pool and benefits from raising caps or switching to Fill First remain unproven. The existing deadline-driven cancellation path already released abandoned requests in the transport acceptance described below. Both account strategies preserve the requested model. [Official capacity and routing semantics](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/README_en.md)

### Runtime & channels

| Setting | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| `WAA_BACKEND` | SpiderMonkey → same | Startup logs confirmed SpiderMonkey | `spidermonkey` | Editable, next generation-service start | Retain the in-process backend |
| `UPSTREAM_CHANNELS` | Playground only → same | Playground only. All 17 historical native ledger entries used it | `playground` | Playground is required in this GUI. Build toggle editable, next generation-service start | Keep Build off. Developer API and Vertex are outside this path |
| `BUILD_NATIVE_NONSTREAM` | Default On → same | Dormant because Build is off | On | Hidden with Build off, next generation-service start | Preserve the dormant setting |
| `INIT_TIMEOUT` | `2m` → same | Applied to per-account WAA initialization | `2m` | Editable, next generation-service start | Keep the account initialization ceiling |
| `REQUEST_TIMEOUT` | `30m` → same | Native execution ceiling per continuation round | `30m` | Editable, next generation-service start | Preserve current deadlines |
| `FIRST_EVENT_HEDGE` | Off → Off | Off. Custom threshold input hidden | Off | Editable, next generation-service start | Keep duplicate upstream generation disabled |
| `FIRST_EVENT_HEDGE_MODELS` | `gemini-4-argon` → same | Dormant while hedge is off | `gemini-4-argon` | Model selector, next generation-service start | Preserve the inactive target |

The Bridge has a 115 s native header/idle timeout. Caddy's internal response-header boundary is 120 s, the router connection-to-headers boundary is 130 s, and the installed Windows Codex transport has a 180 s total per-request deadline. They govern different segments or phases. A Bridge SSE heartbeat can arrive before provider content. Previous live acceptance observed cancellation propagate to native HTTP 499 at about 177.5 s. The current audit had zero in-flight calls and made no new cancellation or generation sample. [Prior live transport and Codex evidence](master-plan-v10-execution.md#p3--latency-and-reliability)

### Models & protocols

| Setting | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| `MODEL_MAPPING` | Seven custom aliases → same | Existing aliases below | Empty | Editable, immediate | Preserve current or unresolved native consumers |
| `MODEL_CHANNELS` | Empty → empty | Global Playground policy applies | Empty | Editable in Models or model details, immediate | No per-model channel exceptions needed |
| `MODEL_ACCOUNTS` | Five persisted entries → same | Real Flash unbound, Lite seven scoped seats, Argon three | Empty | Editable in models/detail, immediate | Preserve real-model and redundant alias entries pending consumer verification |
| `NONSTREAM_KEEPALIVE` | On → On | Configured for non-streaming requests | On | Editable, immediate | Retain non-streaming connection keepalive |
| `FAKE_STREAM` | Off → Off | Off | Off | Editable, immediate | Preserve incremental streaming where supported |
| `YOUTUBE_LINKS` | Off → Off | No URL-to-video handling enabled | Off | Editable, next generation-service start | No approved consumer requirement |
| `SEARCH_MODEL_ALIASES` | On → On | Existing search suffix alias behavior | On | Editable, immediate | Preserve native compatibility |
| `DISCOVER_HIDDEN_MODELS` | Off → Off | No active probing enabled | Off | Editable, next generation-service start | Existing labeled rows can still appear in the catalog |
| `GOOGLE_SEARCH` | Off → Off | No global injection of Google Search | Off | Editable, immediate | Preserve per-request and alias behavior |
| `CONTINUATION_REWRITE` | On → On | Configured to rewrite a trailing assistant turn | On | Editable, next generation-service start | Keep continuation compatibility pending client evidence |
| `CONTINUATION_PROMPT` | Built-in English prompt → same | Default prompt active with rewrite | Built-in English prompt | Editable while rewrite is on, next generation-service start | Keep existing prefix-aware continuation instructions |
| `STRIP_THOUGHT_SIGNATURES` | Off → Off | Retain thought signatures when provided | Off | Editable, next generation-service start | Preserve provider state needed for compatible tool turns |

### Network

| Setting or readout | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| Global `PROXY` | Empty → empty | Current egress reported Direct | Empty | Editable, next generation-service start | Retain shared native German egress |
| Proxy pool | No configured entries → same | Health panel idle, no configured pool to assess | No pool | Configured through the global proxy field | No proxy infrastructure required |
| Account proxy overrides | Empty on all ten records → same | Ten GUI entries Direct. Read-only coverage confirmed zero overrides | Blank, inherits the global setting | Accounts → Edit, save per account | Preserve existing account egress and sessions |

The console showed a shared German exit, `de-DE` and `Europe/Berlin`. Logs showed past account authorization errors and cancellations. The deferred Flash evidence locates the strongest observed wait at upstream response headers and leaves its cause unresolved. The current audit established no proxy-specific failure and no grounds for an egress change.

### Security

| Setting | Saved → after reload | Active or applicable state | v0.3.12 default | GUI and effect of a change | Decision and purpose |
| --- | --- | --- | --- | --- | --- |
| `ADMIN_AUTH_ENABLED` | On → On | Authenticated console. Anonymous management GETs denied | Off | Editable, management restart | Preserve remote administrator authentication |
| `ADMIN_USERNAME` | Existing default administrator → same | UI showed an authenticated session for that identity | Built-in administrator | Editable, management restart | Preserve the established identity |
| `ADMIN_PASSWORD` | Configured → configured | Password presence confirmed. Write-only GUI field left blank | Empty | Write-only, management restart. Blank preserves existing value | Keep current credential |
| `REQUEST_BODY_LOG` | Off → Off | No stored request bodies in the inspected ledger | Off | Editable, immediate | Minimize retention of sensitive prompt and response content |
| `LOG_FILE` | On → On | File logging active | On | Editable, immediate | Keep operational diagnostics |
| `LOG_MAX_TOTAL_MB` | 500 → 500 | Total file cap 500 MB. Observed file log size about 1 MiB and root free space 29 GiB | 500 MB | Editable, immediate rotation policy | Preserve current retention budget |

**PASS · configuration decision.** No setting cleared the evidence and impact gates for a change. No Save, account action, lifecycle action, or update was needed. No rollback was needed. For a future authorized change, revert in the same GUI section by restoring the captured earlier value, then reload and verify the active value. For model bindings use **Model catalog → real-model details**. Settings that need a restart should be confirmed through the appropriate official lifecycle control after checking for active work. Credential changes require a separately authorized rollback plan. Listener changes risk losing console access. Capacity and routing edits risk changing available slots, distribution and retry behavior. Runtime and model edits risk changing request semantics and billing exposure. Logging edits affect diagnostic retention and privacy.

## Accounts and model selection

**PASS · inventory.** All ten account records were enabled, eight Ready and two Restricted. The Ready group was six Free and two Pro. The Restricted records were one Free and one Pro. No row was in the separate Auth required state. Each row reported 49 catalog models. The GUI displayed the two Ready Pro rows, six Ready Free rows, then the two Restricted rows. This display order leaves the saved Fill First ordering empty. The audit opened one account's Edit form and dismissed it without saving. The account set matched before and after.

**BLOCKED · owner Google verification.** Both Restriction → Reason dialogs directed the account owner to [official Google AI Studio account verification](https://aistudio.google.com/verify-account). The owner needs to complete that Google flow for each affected account. After that, authorize one GUI Refresh per verified account and check whether it returns to Ready. The tagged native implementation can send one generation request when manually refreshing a record with this verification reason. A general last-refresh value for every account was **UNKNOWN**. One row exposed an original-computer renewal time. Read-only model-access timestamps covered 20 entries from 17:16:41 through 17:34:05 UTC and describe access checks. [Official Accounts UI](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/web/src/components/AccountsPanel.vue) · [Native restriction and refresh semantics](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/docs/development.md)

### Native aliases

| Alias | Real model | Saved alias-level binding |
| --- | --- | --- |
| `cursor-argon-vps` | `gemini-4-argon` | Three seats, same list as real-model scope |
| `cursor-coding-combo-vps` | `gemini-4-argon` | None |
| `cursor-flash3.5-vps` | `gemini-3.5-flash-lite` | Seven seats, same list as real-model scope |
| `cursor-free-vps` | `gemini-3.5-flash-lite` | Seven seats, same list as real-model scope |
| `cursor-coder-vps` | `gemini-4-hydrogen` | None |
| `cursor-flash3.8-vps` | `gemini-3.8-flash` | None |
| `cursor-combo-vps` | `gemini-3.8-flash` | None |

The Combo-named aliases each resolve to one model. The native request path resolves aliases to real IDs for model selection. The three alias-level bindings mirror their targets and are redundant on that path. Alias cleanup is **DEFERRED** pending verification of direct native consumer dependencies.

### Real-model catalog

**PASS · inventory / PARTIAL · capability evidence.** All seven real IDs were present. Model details showed Playground, function declarations, Thinking and media-resolution controls. The inspected models shared a listed 1,048,576-token input limit. The GUI advertised `generateContent`, `countTokens` and `batchGenerateContent`. Native Gemini metadata GETs listed `generateContent` and `countTokens` for all seven, plus `createCachedContent` for the four Flash-family IDs. The catalog also contains distinct specialized media and hidden entries. Its tool and media metadata establishes advertised capabilities. Live multimodal execution, Thinking behavior, provider entitlements and streaming for the five additionally inspected candidates remain **UNKNOWN**; the public Gateway does not offer batch, cached-content, or native Gemini routes. Previously accepted public text streaming and Chat tool round trips apply to the existing Flash and Lite scopes. [Model eligibility history](model-eligibility-matrix.md) · [Tagged Models UI](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/web/src/components/ModelsTable.vue)

| Real model | Saved selector | Ready eligibility snapshot | Catalog tier flag | GUI / native metadata output tokens | Gateway status |
| --- | --- | --- | --- | --- | --- |
| `gemini-3.8-flash` | All, no binding | 8 | Unflagged | 65,536 / 65,536 | Production, prior bounded execution verified |
| `gemini-3.5-flash-lite` | Seven Free seats | 6 Free | Unflagged | 65,536 / 65,536 | Isolated pilot, prior bounded execution verified |
| `gemini-3.1-flash-lite` | All, no binding | 8 | Unflagged | 65,536 / 65,536 | **BLOCKED** for expansion |
| `gemini-3.6-flash` | All, no binding | 2 Pro | Paid, catalog tier filter | 65,536 / 65,536 | **BLOCKED** for expansion |
| `gemini-4-argon` | Three Pro seats | 2 Pro | Paid, catalog tier filter | 1,048,576 / 32,768 | **BLOCKED** for expansion |
| `gemini-4-hydrogen` | All, no binding | 8 | Unflagged | 1,048,576 / 65,536 | **BLOCKED** for expansion |
| `gemini-4-neon` | All, no binding | 2 Pro | Paid, catalog tier filter | 1,048,576 / 65,536 | **BLOCKED** for expansion |

For Argon, Hydrogen and Neon, the tagged GUI's `outputLimit` uses the input limit when the catalog indicates output continuation. The native Gemini model metadata reports a separate `outputTokenLimit`. Use the latter for conservative per-response sizing. The achievable end-to-end ceiling across continuation rounds is **UNKNOWN**. Ready eligibility is conditional on account state, quota and provider acceptance. An unflagged model can still require entitlement or incur charges. [GUI output limit calculation](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/web/src/components/ModelsTable.vue) · [Native eligibility code](https://github.com/Mag1cFall/AIStudio2API/blob/v0.3.12/internal/aistudio/accounts.go)

## Production checks

The public path is Client → Caddy → Edge Guard → 9Router → Private Bridge → AIStudio2API → Google AI Studio Playground. Native management and generation health returned OK, and the process, Caddy/Bridge fingerprints and router identity matched preflight. Edge Guard, Bridge and dedicated egress stayed active. The router still had one private Bridge provider and zero combos, with container egress limited to the approved private destination. No direct configuration writes occurred.

Public production uses the scoped [Free-First Gateway](https://r9.185-221-237-84.sslip.io/v1). The separate native origin on the same VPS has its own access policy. Anonymous native GETs to `/v1/models`, `/api/config` and `/api/accounts` returned 401. The existing API key and console authentication are active. Credential strength, rotation or destructive testing were outside the authorized audit.

| Check | Status | Evidence |
| --- | --- | --- |
| GUI session, version, persisted values, effective service | **PASS** | Signed-in admin, v0.3.12 running, six Settings groups matched after reload, no pending restarts, matching VPS process and fingerprints |
| Gateway canary, Windows Codex and Windows Cursor keys | **PASS** | Each catalog returned exactly `free/gemini-3.8-flash`. Windows checks used installed DPAPI credentials |
| Gateway Lite pilot key | **PASS** | Catalog returned exactly `free/gemini-3.5-flash-lite` |
| PR #12 default-deny contract | **PASS** | Across all four keys, missing and invalid credentials returned 401, GET on Chat and Responses returned 405, and the unsupported route returned 404. Public Anthropic and Gemini probes separately returned 404 |
| Native provider policy and request ledger | **PASS** | Playground only, no new metered provider route. Ledger count stayed at 17 with the same final entry, so the audit added no recorded generation or retry |
| Logs, Cooldowns & requests, Usage, Access (Connect) and Version | **PASS** | Observed startup and warm-up, prior 499s and account errors, zero active requests/cooldowns, and 17 historical requests including three cancellations. Access showed native endpoint documentation. Version showed Up to date |
| Isolated router fixtures at the reviewed PR head | **PASS / BLOCKED** | Synthetic protocol/streaming and failover checks passed within accepted scope. Negative controls exposed unsupported Gemini tools/catalog policy and capability-unsafe Combo selection. Public promotion remains blocked |
| Fresh generation, Access test action and load benchmark | **NOT_RUN** | Prior scoped smoke and cancellation evidence retained. The audit used GET-only verification |
| Installed Codex tool-result continuation | **FAIL** | Prior live continuation timed out. Most recent rerun stalled before the tool call; continuation and resume in that rerun were **NOT_RUN** |
| Provider billing and per-candidate entitlements | **UNKNOWN** | Usage is an estimate. **BLOCKED — OUTSIDE OFFICIAL GUI** for provider invoices and owner account verification |
| Flash latency | **DEFERRED — UNRESOLVED — MONITOR PASSIVELY** | No Flash account-scope change, Free-only experiment, hedge, or latency benchmark. The earlier Pro-scoped association and provider-side cause retain their existing classifications |

## Onboarding checkpoint

The existing Gateway is ready for connection preflight for a separately approved non-IDE consumer that uses OpenAI Chat Completions or Responses. Identify the application and owner, required endpoint and scoped model, expected concurrency, streaming and tool-result behavior, and credential storage and data-retention needs. Use the existing onboarding contract and obtain approval for a dedicated one-model key and a bounded live acceptance call. Run the GET-only checker and require the actual application to pass its approved live call before onboarding is complete. Gemini, Anthropic, Combo, and other public protocol changes remain **BLOCKED** pending their own authorization and acceptance gates. [Client onboarding contract](client-migration.md#application-onboarding)
