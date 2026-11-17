---
name: paperclip-resume-session-placeholder-guard
description: Debug and fix Paperclip issue-workflow resume paths when a literal placeholder session id (especially "from") leaks into Hermes/OpenCode resume params. Add a regression test and verify with a targeted test.
metadata:
  category: software-development
---

# Paperclip Resume Session Placeholder Guard

Use this skill when a Paperclip issue-workflow or heartbeat resume path fails with an invalid literal session id, especially errors like `Session not found: from`.

## Goal

Find the exact resume-session source, prevent placeholder values from being forwarded to the adapter, and add a regression test that proves the invalid value is dropped.

## Workflow

1. Reproduce and trace the failing path.
   - Search for `resumeSessionParams`, `resumeSessionDisplayId`, `sessionIdBefore`, `sessionIdAfter`, `buildExplicitResumeSessionOverride`, and any adapter launch code that forwards resume IDs.
   - Identify whether the bad value comes from issue wakeup, task session reuse, heartbeat migration, or a display-id fallback.

2. Inspect the resume-override logic.
   - Check the code that builds adapter `--session` params and the upstream resume builder that feeds it.
   - Verify whether a fallback or placeholder value can be serialized into `sessionId`.
   - Watch for literal placeholder strings that originate from templated payloads or malformed context, especially `"from"`.
   - If the adapter itself has a resume option, sanitize there too, but treat the upstream builder as the preferred fix point.

3. Fix at the source.
   - If the resume id is a placeholder, return `null` or omit `sessionParams`/`sessionDisplayId` rather than forwarding it.
   - Keep the fix minimal and preserve valid resume behavior.
   - If the live workflow later reports 401/403 after resume succeeds, treat that as a separate auth/actor-context problem rather than a resume-ID problem.

4. Add a regression test.
   - Cover the invalid placeholder case explicitly.
   - Assert that the builder returns `null` or does not emit `sessionId: "from"`.
   - Keep existing valid resume cases intact.

5. Verify.
   - Run the most targeted test file(s) first.
   - If needed, run the adjacent process-recovery or live-equivalent test that exercises the wake/resume path.
   - For live verification, prefer checking the current health endpoint after a restart rather than assuming the old port is still active.

## Notes

- The issue can look like an adapter/session problem, but the root cause is often a bad upstream resume payload.
- Prefer guarding the resume builder instead of patching adapter parsing to ignore an obviously invalid id.
- If a placeholder literal appears in a real resume path, treat it as tainted input and do not resume.
- In Paperclip dev environments, stale listeners on ports 3100/3101/13100 can cause confusing restart behavior; clear them before assuming the new server failed.

