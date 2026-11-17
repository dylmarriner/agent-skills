---
name: adapter-session-resume-hardening
description: Harden agent adapter resume flows so malformed, placeholder, or stale session IDs never get passed through as literal resume IDs. Use when debugging or implementing session resume logic in Paperclip/Hermes-style adapters.
---

# Adapter Session Resume Hardening

Use this skill when an adapter accepts a previous session identifier from runtime state, request context, or persisted params and uses it to build a resume command such as `--resume` or `--session`.

## Goal
Prevent bad values like placeholder tokens, empty strings, or stale session IDs from being treated as real resume identifiers.

## What to do

1. Read the runtime session source carefully.
   - Check both `runtime.sessionId` and `runtime.sessionParams`.
   - Normalize before use: `trim()` and `readNonEmptyString`-style validation.

2. Reject placeholder literals explicitly.
   - Treat template artifacts like `from`, `to`, `null`, `undefined`, or other known placeholders as invalid if they can appear in the data path.
   - Do not assume a non-empty string is valid.

3. Reuse only when the session is actually safe to resume.
   - Verify cwd/workspace match if the adapter scope depends on location.
   - Verify any adapter-specific constraints before passing the ID to the CLI.

4. Fall back to a fresh session when invalid.
   - Set `sessionId = null` or equivalent.
   - Ensure the adapter builds the launch command without resume flags.
   - Add a log line explaining that resume was skipped and why.

5. Verify the behavior.
   - Add a targeted regression test if possible.
   - Assert that invalid placeholder values do not appear in the final command args.
   - If testing live, confirm the adapter starts fresh instead of attempting to resume.

## Pitfalls

- A placeholder can survive as a literal string if it comes from templating, URL params, or serialized state.
- Do not rely on downstream CLI errors to catch this; sanitize before command construction.
- Avoid mixing stale-session handling with placeholder sanitization in one opaque branch. Keep the invalid-input case explicit.
- If the adapter can recover by retrying, make sure retry logic does not re-inject the original invalid resume ID.

## Good pattern

- Normalize input
- Reject known bad literals
- Validate scope/cwd
- Resume only when all checks pass
- Otherwise start fresh and log why

## Verification checklist

- Invalid placeholder value is converted to fresh-session behavior
- Resume flag is omitted from launch args
- Fresh-session warning/log is emitted
- Regression test covers the bad literal path
