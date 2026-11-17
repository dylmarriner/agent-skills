---
name: secure-messaging
description: Recommend secure/anonymous messaging apps with analysis of metadata resistance, identifiers, and police-recoverable data. Covers SimpleX, Signal, Session, Briar, Telegram, WhatsApp.
---

# Secure Messaging App Guidance

## When to use this skill
- User asks: "most secure messaging app", "anonymous messaging", "untraceable chat", "police-proof messaging", "best privacy app", "messages not recoverable by police", or similar privacy-focused questions.
- User compares Signal vs Telegram vs WhatsApp vs Session vs SimpleX vs Briar.
- User asks about message recovery, encryption, metadata, or subpoena resistance.

## Core framework — three criteria

When evaluating any messaging app for high security, assess against these three axes:

1. **Identifier requirement** — does the app need a phone number, email, or username? Anything tied to real identity is a subpoena point.
2. **Metadata resistance** — does the server/network know who talks to whom, when, from which IP?
3. **Recoverability** — after delivery, can a third party (police, server operator) recover conversation contents?

## The hierarchy

### Tier 1 — No identifiers, no serverside records (recommend for anonymity)
- **SimpleX** — No phone/email/username/ID at all. One-time connection addresses deleted after use. Messages deleted from relay immediately on delivery. No cloud backup. No server-side conversation history. Best practical tradeoff between security and usability.
- **Briar** — True P2P over Tor/Bluetooth. No servers. Both parties must be online simultaneously. Most resilient but least practical for daily use.

### Tier 2 — Pseudonymous, good metadata resistance
- **Session** — No phone number. Random ID on Oxen blockchain. IP hidden via onion routing. Oxen node operators can see traffic patterns. Slightly more metadata exposed than SimpleX.

### Tier 3 — Encrypted but identifier-linked (avoid for anonymity)
- **Signal** — End-to-end encrypted. **Requires phone number.** Metadata visible to Signal servers (who talks to whom, when). Police can subpoena carrier for identity. Active messages on unlocked device readable if seized.

### Tier 4 — Low security (avoid entirely for sensitive use)
- **WhatsApp** — Meta-owned, shares metadata, tied to phone number.
- **Telegram** — Not E2E by default (only Secret Chats). Server stores all regular messages.

## Truths to state upfront
- No app is 100% untraceable. Say "best available" and explain weak points.
- The app is always the strongest link. The user's device (unlocked phone seized) and their behaviour (buying with traceable payment, accessing from home IP) are weaker.

## SimpleX message recovery — detailed
- **In relay queue (undelivered):** Recoverable encrypted blob if relay seized. Can't read content without device key. Metadata: "something sent to someone at time X."
- **After delivery:** Deleted from relay. No server copy. No cloud backup. No subpoena target.
- **After auto-delete fires on device:** Deleted locally. If phone seized before timer expires, messages are readable.
- **Real weak point:** Unlocked device. Full-disk encryption + strong PIN + auto-app-lock are mandatory.

## Signal message recovery
- **From Signal servers:** E2E encrypted, but metadata (who, when) is logged. Phone number required = carrier subpoena identifies user.
- **From cloud backup:** If backup enabled and subpoenaed, messages readable.
- **From device:** Same as SimpleX — unlocked device = all messages readable.

## What NOT to say
- "100% untraceable" or "police can never recover this"
- Recommend Signal/WhatsApp/Telegram when user asks for full anonymity
- Claim any app is perfect against a state-level adversary with physical device access

## Related reference file
- `references/app-comparison.md` — full detailed comparison table from the source conversation
