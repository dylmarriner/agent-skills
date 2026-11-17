# Changelog

All notable changes to the DeepSweep VS Code Extension.

## [Unreleased]

## [1.13.1] - 2026-06-24

### Changed
- **Marketplace listing rewritten to lead with "Review My Agent Environment"** and brought into ADR-RGOV-012 lexicon compliance. The 1.13.0 listing shipped with the pre-M2 "Close the Verification Gap" headline and used banned product nouns ("security scanner", "Validation" as a feature/CTA noun); the README now headlines the 1.13.0 flagship — the one-command local agent-environment review — documents `DeepSweep: Review My Agent Environment` in the Commands table, and adds an Agent Authorization Gaps detection row. The `package.json` marketplace description was updated to match. Listing copy only — no code, pricing, command, or telemetry changes.

## [1.13.0] - 2026-06-24

### Added
- **Review My Agent Environment** — a new command (`DeepSweep: Review My Agent Environment`) that performs a local, metadata-only review of your AI agent setup: it detects the agent's capabilities (MCP tool access, shell execution, database access, repository write, deploy), derives a deterministic local agent identity, and evaluates an advisory authorization policy to surface gaps where an agent can act beyond what it should. Runs fully on-device — no account, no cloud, no source upload.
- **Agent identity** — deterministic local derivation of an `AgentIdentity` from workspace metadata, so reviews are stable and reproducible across runs.
- **Advisory authorization** — `evaluatePolicy()` is wired into the review to report authorization gaps as advisory findings (no enforcement; enforcement is the future Protect tier, gated on demand).
- **G-PMF instrumentation** — privacy-safe demand/activation signals for the Review tier: `review:started`, `review:completed`, `review:error` (metadata only — capability counts, gap count, overall risk; never source or file contents).

### Notes
- The Repo Grade and AI Code Health Score remain free forever. The Agent Environment Review is available without an account.
- Additive release: no changes to existing validation, pricing (ADR-PRICING-002), or telemetry-privacy posture.

## [1.12.0] - 2026-06-18

### Changed
- **One-voice pricing across the upsell ladder.** Panel CTAs, code-action labels, tree-view upsells, the marketplace README, and the onboarding walkthrough now all reflect the canonical Pro $19/mo · Team $99/mo lineup (ADR-PRICING-002), matching the website. Removed stale `$9 "Starter"`, `$29`, and `$20` references. The Repo Grade and AI Code Health Score remain free forever — paid tiers unlock the fixes, never the grade.

### Added
- **In-IDE upgrade module + post-install recognition** (`src/upgrade/`): a pure, dependency-injected `UpgradeManager` with a reason-driven playbook and attributed (utm) checkout URLs. Install/activate telemetry now records `workspace_trusted` and `ide_name` for cleaner funnel attribution.

## [1.11.0] - 2026-06-11

### Added
- **AI Code Health Score card**: a shareable "can I ship this?" summary combining your Repo Grade and security score with a deterministic **Deploy Risk** (low / medium / high) and an optimistic, path-to-ship recommendation. New command **DeepSweep: Copy Health Card**.
- Deploy-risk signal is now recorded (privacy-safe metadata only — no source, no file contents) on each validation, so you can see the ship/no-ship trend over time.

## [1.10.2] - 2026-06-10

### Changed
- Marketplace README cleanup: removed an internal strategy document that had been embedded in the listing, and corrected the AI-specific pattern count to be consistent (37 AI-specific + 40 traditional = 77). Added Certify-on-Write to the feature list. No functional changes.

## [1.10.1] - 2026-06-08

### Added
- **Certify-on-Write false-positive signal**: `certify:checkpoint_false_positive` now fires when a checkpoint is accepted with reason "False Positive" (paid tier), completing the telemetry needed to measure the checkpoint's false-positive rate and decide whether the `notify` default stays on.

## [1.10.0] - 2026-06-08

### Added
- **Certify-on-Write**: an always-on guardrail that catches an AI agent the moment it writes a new critical/high-severity finding — before you move on or commit. Turns the passive validator into a checkpoint at the point of write.
  - **Agent-write classifier** distinguishes agent-authored edits (bulk, multi-file, programmatic writes) from human typing, so checkpoints fire on agent output rather than your keystrokes.
  - **Per-file finding baselines** isolate *newly introduced* findings from pre-existing ones — no nagging about code that was already there.
  - **Checkpoint UI** reveals and selects the offending line, then offers one-click **Revert**, **Auto-Fix** (paid), **Review**, or **Accept Anyway**.
  - **Tiered behavior**: `block` (modal) is a paid capability; free/anonymous users fall back to a non-blocking `notify` toast. Governed **Accept Anyway** records a suppression with reason + audit trail (paid) or a session dismiss (free).
  - **Compliance report** gains a `CERTIFY-ON-WRITE CHECKPOINT TRACE` section logging every checkpoint — finding, introducing agent, decision, tier, and time.
  - **Telemetry**: `certify:checkpoint_raised`, `certify:checkpoint_decision`, `certify:checkpoint_false_positive` — instruments the Certification Acceptance Rate and false-positive rate.
- 22 new unit tests (`agentWriteClassifier`, `certificationGateHelpers`). Total suite: 375 passing.

### Changed
- New settings `deepsweep.certifyOnWrite.enabled` (master switch, default on) and `deepsweep.certifyOnWrite.mode` (`off` / `shadow` / `notify` / `block`). **Default is `notify`** — agent-introduced critical/high findings surface an interactive checkpoint out of the box. Set `mode` to `shadow` for calibration-only (no prompt) or `off` to disable.

## [1.9.5] - 2026-05-14

### Added
- **Abandonment & retention instrumentation**: 7 new PostHog events targeting the funnel-exit points the existing 80+ event suite couldn't isolate.
  - `abandonment:activation_no_workspace` — install + activate with zero workspace folders
  - `abandonment:activation_empty_workspace` — folder open but nothing scannable
  - `abandonment:walkthrough_step_abandoned` — walkthrough opened but final step never reached
  - `retention:time_to_value_bucket` — bucketed first-validation latency for cohort comparison
  - `retention:day_bucket` — fires once at each of D1/D2/D3/D7/D14/D30/D60/D90 after install
  - `retention:long_absence_return` — return after 14+ day activation gap
  - `engagement:finding_first_interaction` — first time the user actually engages with a finding (click/copy/apply/dismiss) vs just seeing the count
- 35 new unit tests (`test/retention.test.ts`) covering bucket math, idempotency, threshold behavior, and event-payload shape. Total suite: 353 passing.

### Fixed
- `Cmd/Ctrl+Shift+S` now validates the current file (as documented in the README) instead of the workspace. Workspace validation remains accessible via the command palette and status bar.
- `VERSION` constant in `extension.ts` was hardcoded as `1.8.0` while `package.json` advanced; PostHog `extension_version` properties on the install-event path drifted from the published version. Now resolved at activate-time from `context.extension.packageJSON.version`.
- Marketplace `keywords` missing `windsurf`, `copilot`, `claude`, `prompt injection`, `slopsquatting` — fixes a known test failure and improves search discoverability for the IDEs the README explicitly supports.

### Changed
- **Brand redesign** (carried over from prior Unreleased work): Deep Navy / Cyan / Verification Yellow palette across Security Panel, Welcome panel, and marketplace description.
- **Unified messaging**: marketplace description, gallery banner, walkthrough copy, and Welcome panel headline now lead with a single positioning statement — *runtime security for AI-generated code, closing the verification gap*.
- **README rebuilt for marketplace conversion**: hero badges row, benefit-first lede, "Why DeepSweep" differentiation against traditional SAST, and a 3-step Quick Start above the detection table.
- **Typography**: Security Panel and Welcome panel request Inter (with system-font fallback) and JetBrains Mono for code/status surfaces.
- **Grade colors**: B-tier grades use the cyan brand scale; C-tier "review" state aligns with Verification Yellow.

### Fixed (prior)
- Removed duplicate `deepsweep.showAccount` command entry in `package.json`.

## [1.9.1] - 2026-02-28

### Added
- **Workspace Trust Support**: Extension now activates in untrusted and restricted workspaces — the VS Code default for cloned repos, `create-next-app` projects, Lovable/Bolt exports, and downloaded zips. Validation runs everywhere; code action fixes require full trust.
- **CWE Compliance Mapping**: All 37 security patterns now include CWE identifiers (e.g., CWE-798, CWE-94) for compliance workflows, audit reports, and CI/CD policy enforcement
- **5 New Detection Patterns**: Credential exposure and configuration security coverage expanded across GCP, Azure, Slack, SendGrid, and Twilio
- **InstructionFingerprint**: Understand what your `.cursorrules`, `.windsurfrules`, and AI config files actually instruct your assistants to do — surfaces the Vibe Code Health Index
- **Multi-IDE Support**: Improved compatibility and detection across VS Code, Cursor, Windsurf, VSCodium, and code-server
- **318 Tests**: Comprehensive coverage across workspace trust, pattern detection, and IDE compatibility

### Fixed
- Extension silently failed to activate in untrusted workspaces — the default state for most AI-generated projects in VS Code. Now declares restricted mode support so validation runs immediately on first open.

## [1.8.1] - 2026-02-24

### Fixed
- Auto-validation occasionally failing silently on first workspace open — validation now runs reliably every time
- Incorrect founding member count on the welcome screen
- Dashboard retention metric now displays correctly

## [1.8.0] - 2026-02-24

### Added
- Weekly security digest: get notified about new patterns and detection improvements
- Founding member recognition for early adopters

## [1.7.5] - 2026-02-24

### Added
- **Validation Proof**: See exactly what was checked after every validation — patterns, files, duration, and security grade
- **Validation Proof Panel**: Expandable detail section showing security category coverage, stats, and scope
- **Rules File Backdoor Detection**: 4 new patterns targeting invisible attack vectors in `.cursorrules`, `.windsurfrules`, and AI config files
  - Zero-width/invisible Unicode character detection (critical)
  - Bidirectional text override detection (critical)
  - Base64-encoded payload detection in rules files (high)
  - Hidden HTML/CSS content block detection (high)
- **Improved Badge Sharing**: Badge markdown now includes project-specific tracking and links to a shareable landing page
- **64 Total Security Patterns**: Up from 60 — 24 AI-specific + 40 traditional

### Fixed
- Badge copy now links to project-specific landing page
- Validation footer now shows pattern count alongside file count and duration

## [1.7.4] - 2026-02-23

### Added
- **Status Bar**: Tooltip now shows cumulative protection stats — total validations run, issues caught, and fixes applied
- Improved detection accuracy across long editing sessions

## [1.7.0] - 2026-02-23

### Added
- **Finding Suppression**: Suppress findings with reason categories and optional justification
  - **Free**: Session-only dismiss
  - **Starter**: Persistent suppression with reason picker
  - **Pro**: Persistent suppression with required justification, expiration dates, and compliance audit trail
- **Suppressed Findings Section**: Suppressed findings remain visible in a collapsible section for risk acceptance transparency
- **Unsuppress Command**: Restore suppressed findings to the active list

### Changed
- "Dismiss" renamed to "Suppress" across all UI surfaces

## [1.5.7] - 2026-02-23

### Fixed
- Copy Fix Prompt now works for all pattern types including SQL injection, XSS, and traditional security patterns
- Finding Detail and Fix Hint commands updated with same fix
- Diagnostic source alignment for consistent CodeAction behavior

## [1.5.6] - 2026-02-23

### Added
- **Device Linking**: Sign-in now preserves your validation history and grades across devices

## [1.5.5] - 2026-02-23

### Fixed
- Clearer error messages when validation fails

## [1.5.4] - 2026-02-23

### Fixed
- Correct IDE detection across VS Code, Cursor, and Windsurf

## [1.5.3] - 2026-02-23

### Added
- Seamless device setup on first launch — no manual configuration required

### Fixed
- Improved validation accuracy and reliability

## [1.5.2] - 2026-02-22

### Added
- **Fix All Auto-Correct**: One-click command to apply static fixes across your workspace with progress UI
- **Fix Safety Verification**: Each fix is verified after applying; automatically reverted if new issues are introduced
- **Compliance Audit Trail**: Timestamped record of each fix action and outcome

## [1.5.1] - 2026-02-18

### Fixed
- Improved extension reliability across all VS Code versions
- Fixed rare issue where sign-in errors could disrupt validation

## [1.5.0] - 2026-02-18

### Added
- **Live Validation**: Real-time security validation as you type (800ms debounce, configurable)
- **Incremental Updates**: Single-file grade recalculation (~50ms) on save instead of full workspace scan
- **Grade Improvement Notifications**: Celebrate when your security grade improves
- **Config File Watcher**: Auto-validates when `.cursorrules`, `.env`, or `mcp.json` files change
- **242 Tests**: Comprehensive test suite across 11 test files

### Fixed
- File save no longer triggers expensive full workspace scan
- Debounce timer cleanup on dispose
- Hover command naming consistency
- "Copy fix prompt" now copies the actual remediation prompt
- Removed duplicate status bar items

## [1.4.2] - 2026-02-15

### Changed
- Performance and stability improvements

## [1.4.1] - 2026-02-13

### Added
- Updated extension icons and logo
- Static code fix suggestions with compliance metadata
- Streaming validation results

### Fixed
- Authentication flow reliability
- Score ring centering in circular progress display
- Validation error handling improvements

## [1.4.0] - 2026-02-09

### Added
- **60 Security Patterns**: 20 AI-specific + 40 traditional patterns
  - AI-specific: Credential exposure, prompt injection, data exfiltration, MCP security, misconfigurations, supply chain risks
  - Traditional: SQL injection, XSS, path traversal, command injection, crypto issues, deserialization
- **Local Validation Engine**: Sub-second workspace validation, no network required
- **9 Integrated UI Surfaces**: Status bar, Problems panel, Quick Fix, CodeLens, TreeView, Webview, Output channel, Notifications, Inline decorations
- **Real-time Validation**: File-save triggers debounced validation
- **Config File Monitoring**: Auto-validates when AI config files change
- **AI Assistant Detection**: Identifies which AI tool generated the code
- **CVE References**: Patterns linked to known CVEs (CVE-2025-54135, CVE-2025-55284)
- **Badge Copy**: Generate and copy security badge markdown for your README

### Changed
- Validation runs locally first — no network dependency for core scanning
- Optimistic, clear status messages throughout

## [1.3.3] - 2026-02-08

### Added
- Local pattern engine with 40+ security patterns
- Package typosquat detection for npm, PyPI, Go, and Cargo
- Automatic AI assistant detection (Cursor, Windsurf, Copilot, Claude, and more)
- Status bar with [PASS]/[WARN]/[FAIL] indicators
- Inline editor decorations and webview finding panel

## [1.3.0] - 2026-02-07

### Changed
- Extension now works immediately with zero setup — no CLI install required
- Simplified to 4 core commands: Validate Project, Show Report, Sign In, Sign Out

### Added
- GitHub OAuth sign-in
- Auto-validate on workspace open (configurable)
- Status bar with grade and color coding

### Removed
- CLI dependency (no longer needed)

## [1.1.5] - 2026-02-05

### Fixed
- Assessment-first user journey improvements
- Command registration stability on hot reload

## [1.1.2] - 2026-02-03

### Fixed
- Improved extension startup reliability

## [1.1.0] - 2026-02-01

### Added
- First-run experience with auto-validation on install
- Welcome notification with score-based messaging
- Badge prompt for high-scoring projects

## [1.0.0] - 2026-01-29

### Added
- Initial release
- Real-time AI code security validation
- Support for JavaScript, TypeScript, Python, Go, Rust, and more
- [PASS]/[WARN]/[FAIL] status indicators
- Problems panel integration
- Automatic validation on file save
