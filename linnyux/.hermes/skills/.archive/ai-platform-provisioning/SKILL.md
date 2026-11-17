---
name: ai-platform-provisioning
description: "Set up access to AI model API providers: cloud billing troubleshooting, free-trial comparison, signup assistance, and provider configuration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [gcp, vertex-ai, billing, free-trial, cloud-setup, inference-providers, ai-api]
    related_skills: [hermes-agent, linux-proxy-service-management, modal-serverless-gpu]
---

# AI Platform Provisioning

Help users get access to AI model APIs by provisioning cloud accounts, troubleshooting billing issues, comparing free-trial options, and configuring API keys for local tools (Claude Code, OpenCode, LiteLLM, etc.).

## When to Use

Trigger when the user:
- Wants to "get API access" for AI models
- Asks about free credits, trials, or pricing for AI/ML inference platforms
- Has GCP / AWS / Azure billing errors ("billing needed", "BILLING_DISABLED")
- Mentions "Claude Code needs billing" or similar auth errors
- Asks you to sign them up for an AI platform
- Needs an API key for a local AI tool

## 1. GCP Billing Troubleshooting

### Key diagnostic: the `open: false` trap

A GCP project can show `billingEnabled: true` but still fail with `BILLING_DISABLED` from Vertex AI. This happens when the **linked billing account is closed/suspended.** Note the project can also report `billingEnabled: false` directly (2026-08 session: `gcloud billing projects describe` returned `billingEnabled: false` while an account WAS linked — the linked account itself was `open: false`). Both presentations trace to the same root cause: the account behind the link is dead.

Typical user symptom (Claude Code, gcloud, any GCP client):
`API Error: 403 ... "This API method requires billing to be enabled. Please enable billing on project #<ID>"` — the project ID is present, so it's NOT an IAM problem.

```bash
# Check project billing link — this will say True even when broken
gcloud beta billing projects describe <PROJECT_ID>

# Check the billing account itself — THIS is where you find the real issue
gcloud beta billing accounts describe <ACCOUNT_ID>
# Look for: open: false
```

A billing account with `open: false` is closed — no charges can be processed even though the project is linked. Common causes: non-payment, manual closure, payment method expired.

### Fixing it

The user must:
1. Visit https://console.cloud.google.com/billing/create
2. Add a payment method (credit card)
3. Link the new billing account to their project

**Cannot be done via gcloud CLI** or any automated tool. Google's billing pipeline requires user-authenticated Console entry for PCI compliance. Confirmed hard limits (2026-08):
- `gcloud billing accounts create` does NOT exist (invalid subcommand).
- REST `POST https://cloudbilling.googleapis.com/v1/billingAccounts` with `{"displayName": ...}` returns `400 INVALID_ARGUMENT` for standalone accounts — the API only serves sub-accounts under a reseller master, not top-level creation.
- A CLOSED billing account cannot be reopened by API or CLI. The only remediation is a NEW account created in the Console, then linked:
  `gcloud billing projects link <PROJECT_ID> --billing-account=<NEW_ACCOUNT_ID>`

## 1b. IAM Role-Request Remediation (GCP)

Trigger: user forwards a GCP "role request" email / console link (someone requesting a role on a resource, e.g. a collaborator hitting 403 trying to use Claude Code against the project).

Diagnostic order that pins root cause fast:
1. `gcloud auth list` + `gcloud config list` — confirm identity and active project
2. `gcloud projects describe <PROJECT_ID>` — confirm project ACTIVE (don't assume from the email)
3. `gcloud billing projects describe <PROJECT_ID>` — check `billingEnabled`
4. **IF the failing client is Claude Code, check §1c BEFORE this step** — a local
   `CLAUDE_CODE_USE_VERTEX` env override in `~/.claude/settings.json` can cause the same 403 with
   zero GCP involvement needed. Only after ruling out the local override, proceed:
   `gcloud billing accounts describe <ACCOUNT_ID>` — **`open: false` = closed account = 403 root cause** (see §1). The "requires billing to be enabled" 403 is usually billing, NOT IAM — but for Claude Code specifically, the local Vertex override comes first (see §1c).
5. `gcloud projects get-iam-policy <PROJECT_ID> --format=json > /tmp/iam.json` — dump to file, then parse with python. Check whether the requestor already holds a role.

Then remediate:
- Grant the requestor a role on the project. `roles/editor` is the right default for a collaborator who needs to index/build/run (covers Claude Code project work, GCS, Cloud Build, AI Platform). Escalate to `roles/owner` only if they genuinely need IAM/billing management.
  ```bash
  gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="user:EMAIL" --role="roles/editor" --condition=None
  ```
- VERIFY the binding landed: re-dump the policy to a file and grep for the member. Never trust the add command's truncated tail output.
- Billing enablement stays with the project owner (Console-only, see §1) — hand the user the exact console steps, don't promise automation can do it.
- The troubleshooter token in the request email checks `resourcemanager.projects.createBillingAssignment` + `resourcemanager.projects.get` — these are the permissions the requestor was missing; granting editor + enabling billing resolves both.

Worked example with real commands/output for project ai-system-495310: `references/gcp-role-request-remediation-2026-08.md`.

## 1c. The Claude Code Vertex-override trap (check LOCAL config before GCP)

**THE lesson from the 2026-08 ai-system-495310 session: a "requires billing to be enabled" 403 in Claude Code is often NOT a GCP account problem at all — it is a local Claude Code config that silently reroutes model calls through Google Vertex AI on a dead-billing project.** The GCP billing investigation can be a complete red herring; the fix may be one env var.

Trigger: user hits `API Error: 403 ... "This API method requires billing to be enabled. Please enable billing on project #<ID>"` inside Claude Code, insists "I'm using Claude Code, not Google" / "I'm not using Gemini", or asks "why do my other computers work?"

Diagnose LOCAL config FIRST (before touching gcloud):

```bash
# 1. The smoking gun: Vertex env override in Claude Code settings
cat ~/.claude/settings.json          # look for "env": { CLAUDE_CODE_USE_VERTEX, ANTHROPIC_VERTEX_PROJECT_ID, CLOUD_ML_REGION }
cat ~/.claude/settings.local.json    # same check
# 2. Confirm the login path: Anthropic OAuth (sk-ant tokens) vs API key vs Vertex
python3 -c "import json;d=json.load(open('$HOME/.claude.json'));print(d.get('oauthAccount',{}))"
# 3. Find WHICH session/machine hit the error and what triggered it
grep -l "<PROJECT_ID>" ~/.claude/projects/*/*.jsonl    # session logs
```

Read the session JSONL context around the error — the 403's `details` metadata will name the failing service. `aiplatform.googleapis.com` = Vertex routing (the trap). `api.anthropic.com` = genuine Anthropic-side billing/plan issue.

Key tell: if the account shows `billingType: google_play_subscription` on the oauthAccount, that is just the PAYMENT METHOD for the Claude subscription (billed via Google Play) — NOT evidence of GCP involvement. Do not conflate the two.

### Fix (the actual one that worked)

Claude Code has a native Vertex AI integration controlled by env vars in `~/.claude/settings.json`. If the user's other machines work and this one 403s, diff the settings:

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak.vertex-$(date +%Y%m%d-%H%M%S)
# remove the "env" block containing CLAUDE_CODE_USE_VERTEX / ANTHROPIC_VERTEX_PROJECT_ID / CLOUD_ML_REGION
```

After removal, Claude Code talks to Anthropic directly with the user's Pro subscription — matches the working machines. The GCP project becomes irrelevant to Claude usage. Restart Claude Code / start a fresh session.

### When billing IS still needed

Only if the user WANTS the Vertex route (e.g. 1M-context Sonnet via Vertex): create a billing account at console.cloud.google.com/billing, link the project, then re-add `CLAUDE_CODE_USE_VERTEX: "1"` + `ANTHROPIC_VERTEX_PROJECT_ID` + `CLOUD_ML_REGION`. Backed-up settings file at `~/.claude/settings.json.bak.vertex-*`.

Worked detail (session logs, exact settings.json, cross-machine comparison): `references/claude-code-vertex-override-2026-08.md`.

## 2. Free Trial / Credit Comparison

See `references/free-trial-comparison.md` for a full table of platforms, credits, card requirements, and model availability.

Highlights:
- **Groq** — only platform with a genuinely free tier (no card needed). Fast LPU inference on open models.
- **Together AI, DeepInfra, Fireworks AI** — $100 free credits, card required, Google OAuth signup
- **Google Cloud** — $300 free, needs card and billing setup
- **Azure** — $200 free, Azure OpenAI Service

## 3. Automated Signup Limitation

All major AI API platforms use **reCAPTCHA** or **Google OAuth** that block automated/headless browser signup. The agent can:
- Open the signup page
- Pre-fill non-payment fields
- Walk the user through remaining steps
- Configure the service once access is granted

The agent CANNOT:
- Sign the user up autonomously
- Pass reCAPTCHA challenges
- Enter credit card details
- Complete Google OAuth from a headless browser

## 4. Post-Provisioning Setup

Once the user has an account and API key:

### Configure for Claude Code
```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_VERTEX_PROJECT_ID": "your-project",
    "CLOUD_ML_REGION": "us-central1",
    "CLAUDE_CODE_USE_VERTEX": "1"
  }
}
```

### Configure for LiteLLM
```yaml
# litellm-config.yaml
model_list:
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: your-project
      vertex_location: us-central1
```

### Configure for OpenCode
```json
// ~/.config/opencode/opencode.json
{
  "provider": "openrouter",
  "model": "deepseek/deepseek-chat",
  "apiKey": "..."
}
```

## Pitfalls

- **Claude Code Vertex env override beats the login choice.** `CLAUDE_CODE_USE_VERTEX=1` in `~/.claude/settings.json` silently reroutes all model calls through Google Vertex AI even when the user picked "Claude subscription" at /login — producing a GCP "requires billing" 403 with a closed billing account as the trigger. Diagnose `~/.claude/settings.json` FIRST, before any gcloud work (see §1c). Same for ANTHROPIC_BASE_URL pointing at an OpenRouter/Vertex gateway.
- **rtk corrupts piped gcloud JSON.** On machines with the RTK token-killer wrapper, `gcloud ... --format=json | python3 -c ...` breaks — rtk rewrites stdout mid-stream so the JSON parser dies (or worse, parses silently-truncated data). Always write to a file first: `gcloud ... --format=json > /tmp/x.json` then parse the file. Same for `get-iam-policy` verification — never trust the command's own truncated tail.
- **Don't tunnel on one tool.** When the user asks about AI API access, list ALL provider options — they may not care about Claude/GPT and just want working inference. Present open-model platforms alongside proprietary ones.
- **GCP billing accounts can be linked but closed.** `billingEnabled: true` ≠ active billing. Always check `open: false` on the billing account itself.
- **Google OAuth and headless browsers don't mix.** All Google sign-in flows require either residential proxies or user interaction. Most other platforms use reCAPTCHA as a fallback.
- **"Pay at end of month" (invoiced) billing** requires a credit check and contract — not self-service. Users who want this need to contact Google Sales.
- **Free credits expire.** Most $100+ credit offers have a 90-day expiry window.
