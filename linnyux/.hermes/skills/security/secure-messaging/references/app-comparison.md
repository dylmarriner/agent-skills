# Secure Messaging App Comparison

Source: Dylan conversation — asked for "highest security, untraceable, police can't recover"

## Quick Reference Table

| Criteria | SimpleX | Session | Signal | Briar | Telegram | WhatsApp |
|----------|---------|---------|--------|-------|----------|----------|
| **Phone required** | No | No | **Yes** | No | Yes | Yes |
| **User ID type** | One-time temp address | Random ID on Oxen chain | Phone number | Random ID | Phone number | Phone number |
| **E2E by default** | Yes | Yes | Yes | Yes | **No** (only Secret Chats) | Yes |
| **Metadata logged** | Relay sees encrypted blobs only | Oxen nodes see traffic patterns | Server sees who->who, when | Minimal (P2P) | Server stores all metadata | Meta-owned, all metadata |
| **Server-side records** | Deleted on delivery | Messages routed via onion | Retained temporarily | N/A (no servers) | All regular chats stored | Retained |
| **Cloud backup** | None | None | Optional (subpoena-able) | None | Cloud backup by default | Cloud backup |
| **Open source** | Yes | Yes | Yes | Yes | No (client partially) | No |
| **Practical daily use** | Good | Excellent | Excellent | Poor (both must be online) | Excellent | Excellent |

## Police Recovery Assessment

### SimpleX
- **Recoverable while undelivered:** Yes — encrypted blob sits on relay. Can't read content. Can see timestamp.
- **Recoverable after delivery:** No — relay deletes immediately. No copy exists anywhere.
- **Recoverable from device:** Depends on PIN/encryption status and auto-delete timer.
- **Verdict:** Best available. No identifier to subpoena, no server records, no cloud backup.

### Signal
- **Recoverable while undelivered:** Yes — E2E encrypted on server.
- **Recoverable after delivery:** Yes — if cloud backup enabled and subpoenaed.
- **Recoverable from device:** Same as SimpleX — unlocked device = readable.
- **Phone number is the killer:** One subpoena to the carrier and they know who you are.

### Session
- **No phone number** — better than Signal.
- **Oxen blockchain participation** creates slightly more metadata surface than SimpleX.
- **Intermediate option** — good privacy, but SimpleX has less metadata exposure.

### Briar
- **Most resilient** — no servers at all. True P2P over Tor/Bluetooth/direct WiFi.
- **Least practical** — both parties must be online. Messages queued only while both are connected.
- Best for offline-first, mesh-network, or high-adversary scenarios.

## Core Truths
- The app is never the weakest link. Device security and user opsec are.
- Full-disk encryption + strong PIN + automatic app lock are mandatory for any of these.
- "100% untraceable" is a lie. Even SimpleX is vulnerable to: device seizure, rubber-hose crypto, traffic analysis at nation-state level, user opsec failures.
