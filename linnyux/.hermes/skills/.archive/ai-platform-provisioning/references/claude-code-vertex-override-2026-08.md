# Worked detail: Claude Code Vertex-override 403 (2026-08)

Project: ai-system-495310. User: dkmarriner@gmail.com (owner), alt account inhumanekiller22@gmail.com.
Symptom: Claude Code on lin hit `API Error: 403 ... "This API method requires billing to be enabled.
Please enable billing on project #ai-system-495310"` right after `/login` succeeded and the user asked
to index project code.

## What the 403 really was

Claude Code on lin had this in `/home/lin/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "ai-system-495310",
    "CLOUD_ML_REGION": "global"
  }
}
```

That env block is Claude Code's native Google Vertex AI integration. With it set, Claude Code stops
calling Anthropic directly and routes model calls through Google `aiplatform.googleapis.com` on the
given project. The project's billing account was closed (`open: false`), so Google returned
`403 BILLING_DISABLED`, service `aiplatform.googleapis.com`. The user had selected "Claude subscription"
at /login — the env override hijacked the route regardless.

## Evidence trail (commands that pinned it)

1. Session log grep found the error in THIS machine's MUTS project sessions:
   `grep -l "ai-system-495310" ~/.claude/projects/*/*.jsonl` → 4 files under
   `-home-lin-Documents-MUTS/`. The 403 was the assistant's FIRST response to the user's
   "why does this have a node backend" — i.e. every model call was failing, not one tool.
2. Parsed the error line from the JSONL: `details[0].metadata.service = aiplatform.googleapis.com`,
   `reason: BILLING_DISABLED`. That service name is the tell: Vertex routing, not Anthropic.
3. `cat ~/.claude/settings.json` → the env block above. `~/.claude/settings.local.json` was clean.
4. Cross-machine comparison explained "why do my other computers work":
   - kubuntux: `oauthAccount.emailAddress = inhumanekiller22@gmail.com`, billing google_play_subscription — NO Vertex env in settings.json → works
   - macuntu: same account, billing stripe_subscription — NO Vertex env → works
   - lin: same account + Vertex env block → 403
   The only difference between broken and working machines was the env override.
5. `~/.claude/.credentials.json` held real Anthropic OAuth tokens (`sk-ant-oat01-...` / `sk-ant-ort01-...`,
   subscriptionType pro) — proof the subscription itself was fine and the failure was purely transport.

## Fix applied

```bash
cp /home/lin/.claude/settings.json /home/lin/.claude/settings.json.bak.vertex-$(date +%Y%m%d-%H%M%S)
# removed the "env" key (CLAUDE_CODE_USE_VERTEX, ANTHROPIC_VERTEX_PROJECT_ID, CLOUD_ML_REGION)
```
Result: lin now matches kubuntux/macuntu — direct Anthropic, Pro subscription, no GCP involved.

## Traps / takeaways

- `billingType: google_play_subscription` on the Claude oauthAccount = the Claude subscription is
  PAID via Google Play. It is a payment method, NOT a GCP/Vertex integration. Easy to misread as
  "user is on Google" when they are on plain Anthropic.
- Do NOT jump to `gcloud billing` remediation on the first "requires billing" 403 from Claude Code.
  Check `~/.claude/settings.json` env block FIRST. The billing account was genuinely closed, but
  fixing it was optional — the user did not need Vertex at all.
- The error text "Please enable billing on project #<ID>" is Google's format; it appears any time a
  Google API (Vertex included) rejects a call, so it does not by itself mean the user opted into GCP.
- Grep the session JSONL to find WHICH machine and WHICH session hit the error before assuming the
  email's story — the failing call was on lin's MUTS sessions, not on the machine that "sent" the email.
