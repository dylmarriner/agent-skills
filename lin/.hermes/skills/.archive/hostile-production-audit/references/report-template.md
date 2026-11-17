# Hostile Audit Report Template

## Executive Summary

**Target Repository:** `OWNER/REPO`
**Tech Stack:** Next.js / React / Payload CMS / ...
**Overall Verdict:** [NOT PRODUCTION READY / PRODUCTION READY WITH CAVEATS / DEPLOYABLE]
**$NZD Context:** [e.g., "This is a $15K project pretending to be $50K"]

---

## 🔥 TOP 5 FIRES THAT WILL BURN PRODUCTION DOWN

| # | Issue | Severity | Why It's Fatal |
|---|-------|----------|----------------|
| 1 | [Brief title] | Production Collapse | [One-liner consequence] |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

---

## BY CATEGORY

### 🔐 Security (X findings)
| # | Issue | File | Severity | Fix |
|---|-------|------|----------|-----|
| | | | | |

### 🎨 Frontend / UX (X findings)
| # | Issue | File | Severity | Fix |
|---|-------|------|----------|-----|

### ⚙️ Backend / API (X findings)
| # | Issue | File | Severity | Fix |
|---|-------|------|----------|-----|

### 🧹 Code Quality (X findings)
| # | Issue | File | Severity | Fix |
|---|-------|------|----------|-----|

### 🚀 CI/CD & Deployment (X findings)
| # | Issue | File | Severity | Fix |
|---|-------|------|----------|-----|

---

## WHAT'S ACTUALLY GOOD (if anything)

[One component or pattern that's worth the price point. Be honest — credit where due.]

---

## WHAT NEEDS YOUR ACTION (before deploy)

Pre-deployment checklist items that can't be automated:

1. `openssl rand -hex 32` → set as PAYLOAD_SECRET, CRON_SECRET, INLINE_UPDATE_KEY
2. Register [CAPTCHA service] keys at [URL]
3. Rotate [exposed API keys]
4. Set [third-party service credentials]
5. Remove dev hostnames from production config
6. Set [storage/bucket] credentials

---

## BUILD STATUS

✅ / ❌ — Production build: [X pages generated, X errors]

## PREVIOUS AUDIT RECONCILIATION

If a prior audit report exists, note which items were actually resolved vs claimed resolved:
| Claimed Resolved | Actual Status | Notes |
|-----------------|---------------|-------|
| | | |
