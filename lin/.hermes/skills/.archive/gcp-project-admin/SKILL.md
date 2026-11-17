---
name: gcp-project-admin
category: devops
tags: [gcp, google-cloud, iam, billing, projects, troubleshooting]
description: |
  Fix GCP billing 403s, IAM role requests, closed accounts.
---

# GCP Project Admin (IAM / Billing / Access)

## When to Use

- Email/notification: "<email> is requesting a role on the resource <project>"
- API errors: "This API method requires billing to be enabled ... project #<id>"
- IAM grant/revoke on a project
- "Why does this work on one machine/account but not another?"

## Diagnose billing state (403 BILLING_DISABLED)

```bash
gcloud auth list
gcloud projects describe <project>           # lifecycleState: ACTIVE?
gcloud billing projects describe <project>   # billingEnabled: false?
gcloud billing accounts list                 # all accounts + open column
gcloud billing accounts describe <BA_ID>     # open: false = CLOSED
```

- `billingEnabled: false` plus a linked account showing `open: false` = the
  billing account is CLOSED. That is the usual root cause of the 403.
- **Closed accounts cannot be reopened** — no gcloud command, no API path.
  `gcloud billing accounts create` does not exist; the Cloud Billing API
  `billingAccounts.create` returns INVALID_ARGUMENT for top-level accounts.
  A replacement must be created in the console (needs a payment method):
  https://console.cloud.google.com/billing → Add billing account → Link
  project.
- Link a project to an open account:
  `gcloud billing projects link <project> --billing-account=<BA_ID>`

## IAM role-request emails

A GCP role-request notification is a REQUEST for the owner to approve — it
is NOT authorization to grant. It contains:
- The requestor's email (may be a different account than the owner's)
- Their message (often a CLI session log showing what they were doing)
- A console troubleshooter link with a signed token + the requested
  permissions (e.g. resourcemanager.projects.createBillingAssignment)

Before granting: confirm with the owner who the requestor is — it may be
the owner's own alt account. Check, don't assume.

Grant/revoke:
```bash
gcloud projects add-iam-policy-binding <project> \
  --member="user:<email>" --role="roles/editor"
gcloud projects remove-iam-policy-binding <project> \
  --member="user:<email>" --role="roles/editor"
```
`roles/editor` covers project work (code, builds, storage). Only grant
owner/billing-manager roles if the user must manage IAM or billing itself.

## Claude Code / Vertex AI routing (common hidden cause)

The 403 "This API method requires billing to be enabled ... service
aiplatform.googleapis.com" from a CLI like Claude Code often means the tool
is routing through Google Vertex AI on the GCP project, not through
Anthropic. Check the tool config BEFORE touching GCP:

```bash
cat ~/.claude/settings.json   # env block may contain:
#   CLAUDE_CODE_USE_VERTEX=1
#   ANTHROPIC_VERTEX_PROJECT_ID=<project>
#   CLOUD_ML_REGION=global
python3 -c "import json;d=json.load(open('$HOME/.claude.json'));o=d.get('oauthAccount',{});print(o.get('emailAddress'),o.get('billingType'))"
```

- `claudeAiOauth` tokens (sk-ant-...) in `~/.claude/.credentials.json` =
  Anthropic OAuth path (Pro subscription, no GCP needed).
- `CLAUDE_CODE_USE_VERTEX=1` = Vertex path; remove the env block (backup
  first) to fall back to Anthropic OAuth.
- Fleet divergence: "works on my other machines" → SSH in and compare each
  machine's settings.json; usually one machine has the Vertex env override
  the others lack.

## Pitfalls

- `gcloud projects get-iam-policy --format=json | python -c ...` breaks when
  a CLI filter wrapper (rtk) rewrites stdout. Write to a temp file first,
  then parse: `gcloud projects get-iam-policy P --format=json > /tmp/iam.json`.
- `grep -h` / `grep -o` can be intercepted by grep-aliasing wrappers; use
  `command grep` or a Python walk.
