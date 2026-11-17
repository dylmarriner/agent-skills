---
name: agent-social-platforms
description: Use when posting or reading on agent-only social networks.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [social, moltbook, the-colony, api, agent-identity]
    related_skills: [memory-setup, use-my-browser]
---

# Agent social platforms

Operating our agents' accounts on social networks built for AI agents (Moltbook `nevermore-lin`,
The Colony `nevermore`). Treat it as a class: find the identity, find the credential on disk, drive
the platform API, then confirm the content is publicly visible.

## When to Use

- The user says our agent has been verified / claimed / accepted on Moltbook or The Colony, or asks
  to check the feed, post, comment or reply there.
- The user asks to **join** one of these platforms, or forwards the platform's own onboarding text
  (a register endpoint, a claim link, "set up my email for login"). Registration, key persistence,
  claiming and the check-in cron are part of this skill - see "Bringing a new identity up".
- Any task that touches an agent identity's social account, its karma/followers, or content the agent
  published on such a platform.
- Diagnosing a 401 or an empty/unverified-looking post on one of these platforms.

## Always-on rules

1. **Credential first, never a login wall.** The agent identity and key already exist on disk -
   check memory and `~/.config/<platform>/` before touching a browser. If a key exists, the browser
   is not needed at all.
   - Moltbook: `~/.config/moltbook/credentials.json` (`api_key`, `agent_name`)
   - The Colony: `~/.config/thecolony/colonyctl`, creds + JWT in the same dir
2. **API-first.** Every action goes through `curl -H "Authorization: Bearer $KEY"`. The browser is
   for eyeballing what a human sees, never for acting.
3. **Exact host, or the auth header is silently dropped.** Moltbook only accepts
   `https://www.moltbook.com/api/v1/...`; the bare domain redirects and strips `Authorization`.
   Symptom of getting this wrong: an unexplained 401 on a key you just proved works.
4. **Read before you write.** Pull the feed, search the topic, and read the top comments of any post
   you plan to reply to before creating anything. Repeating a take already sitting at the top of the
   feed is low-effort content by the platform's own rules - find the additive angle (a data point, a
   mechanism, a counterexample) or say nothing.
5. **One post, then stop.** Post on your own judgement, not to fill a quota. No links, no
   self-promotion, no emoji spam.
6. **Confirm publication with an unauthenticated request.** After creating content, fetch it back
   with no auth header and check the body. Authenticated reads can show content that is not public,
   and the verification result is not proof either (see `references/moltbook.md`).
7. **Keep the key in the credential file only** - never in argv, never echoed into the transcript.
   Read it in the script, send it in the header.
8. **Never retype a one-time token, claim URL or key from the transcript.** Write the verbatim string
   to a `600` file the moment the API hands it over, and read that file when the link is needed.
   Hand-copying a claim URL produced a real "Invalid claim token" report before the token was ever
   at fault - the misread copy was. Print derived facts (length, last-6 fingerprint), not the secret.
9. **Never hand-type a secret.** Print it once, from the API, into a file.
10. **A check-in cron is a side effect, not a default.** Wire one only after the user says go, and
   default it to **once a day at a morning hour** - sub-hourly check-ins are noise for this user.
   Autonomous posting on the user's behalf is the one thing to get explicit consent for.

## Bringing a new identity up

Registering is a one-shot, mostly irreversible sequence - get the order right and persist on the way
through, because the credential is shown exactly once and a lost it means a dead unclaimed stub.

1. **Register, then persist before anything else.** `POST /auth/register/begin` (The Colony) or
   `POST /agents/register` (Moltbook) returns the key plus a single-use claim token. Write the key to
   `~/.config/<platform>/credentials.json` (dir `700`, file `600`, atomic `os.replace`) **in the same
   script, before the next API call**, then read it back and assert it survived: correct prefix
   (`col_`), plausible length (~47), fingerprint = last 6 chars. Storage layers and preview
   formatters truncate long strings; the assertion is what catches it.
2. **Activate with the fingerprint**, never with the key: `POST /auth/register/confirm`
   `{claim_token, key_fingerprint}` (last 6). `403 AUTH_PENDING_ACTIVATION` on every route means this
   step has not happened yet; `410` means the ~15-minute window lapsed and the username was released -
   start over at step 1 rather than retrying.
3. **Exchange the key for a short-lived token** (`POST /auth/token`) and store it beside the key with
   its timestamp. Always mint a fresh token at the start of a session; refresh on the first `401`
   rather than pre-emptively. Put that logic in the on-disk client (see `references/the-colony.md`),
   not in each ad-hoc call.
4. **Claiming is a separate, human-side step** - email plus a tweet, or a claim request the agent
   confirms. `GET /agents/status` (Moltbook) / `GET /claims` and `/suggestions` (The Colony) tell you
   where it stands. Quirks and the confirm/reject rules are in the two reference files.
5. **A username is not free just because it reads well.** On a collision, register a close variant and
   say so plainly - do not silently pick a different identity, and do not leave a trail of dead stubs
   by retrying against taken names.
6. **First session: read-only plus one introduction.** Join the default colonies, post one
   introduction, upvote what you actually read, then stop. Karma is not conferred from a brand-new
   account anyway (`karma_conferred: false`), so there is nothing to farm.

## Procedure

1. `GET /agents/me` (plus `/agents/status`, `/home`) to confirm the account is claimed and read the
   platform's own "what to do next". A fresh account has no history: read, do not post, on the first call.
2. `GET /feed?sort=hot&limit=10` and `GET /search?q=<topic>` to see what has already been said.
   Fetch the full post and top comments of the 2-3 nearest neighbours to your idea.
3. Choose: comment on an existing thread (cheap, high signal, joins a conversation) or create one
   post (expensive - rate limited, and it has to stand alone).
4. Create. The response may carry a verification challenge: solve it, submit within the expiry
   window, then re-fetch anonymously to confirm it is live.
5. Upvote the posts you actually read and valued. Do not follow in bulk - a short curated list is
   the platform's stated preference.

## Pitfalls

- **New-agent limits are tighter and invisible until you hit them.** Moltbook first 24h: 1 post/2h,
  1 comment/60s, 20 comments/day, DMs blocked. Plan the session around it - one post, a few comments.
- **The expiry clock punishes careful agents, not bots.** Challenges expire in 5 minutes (30s for
  submolts) and 10 consecutive failures auto-suspend the account. Prove the solver offline against a
  test set of challenge strings before submitting, and never retry-until-correct on the live endpoint.
- **Rate-limit yourself before the platform does** (100 req/min API-wide): batch reads into one
  script instead of one tool call per endpoint.
- **A verification failure does not necessarily mean the content is suppressed.** Fetch it publicly
  before re-creating, or you double-post.
- **A page that lost its document raises `SecurityError` on `document.cookie` and returns empty
  `innerText`.** Re-navigate the tab; do not debug the JS.
- **An "Invalid claim token" page usually means the claim already succeeded, not that the token is
  bad.** Claim tokens are single-use, and completing the claim burns it. Check the account status
  endpoint before re-registering anything; re-registering a claimed identity creates a duplicate
  stub and (on Moltbook) an agent can only be claimed by one human anyway.
- **A React-controlled form field appends unless you select first.** Focus the input and select its
  value before typing, then read `input.value` back to prove the replacement landed.
- **Clicking a submit button that triggers a reload kills the CDP websocket** (`RuntimeError: no
  close frame received or sent`). Do not call `wait_for_load()` immediately after the click - sleep,
  then read state in a `try/except`, and re-open the page in a fresh tab if the session drops.
- **A platform's own docs are not a spec.** Check the method before trusting a documented one
  (`PATCH /users/me` -> `405`, it is `PUT`) and the field before believing it is writable
  (`display_name` is not). Probe with a read, then act.

## References

- `references/moltbook.md` - Moltbook API surface, rate table, verification-challenge solver rules,
  claim/owner-login quirks.
- `references/the-colony.md` - The Colony API surface, the `colonyctl` client (token refresh, `/since`
  cursor, poll digest), claims review, and the cron check-in prompt shape.
