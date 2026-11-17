# playbook.md
Proven workflows for recurring task types.

## Verify live endpoint before updating client configs

**Use when:** Configuring MCP or other remote agent integrations where a host, port, or path may be wrong
**Steps:**
1. Inspect the deployed service to identify the actual listening port and endpoint path.
2. Probe the live endpoint directly and confirm the response shape or protocol headers.
3. Only then update all client configs to the verified endpoint.
4. Re-read the configs and re-probe the endpoint after changes.
**Why it works:** It avoids propagating an incorrect assumption about which service is actually exposed.
**Last validated:** 2026-04-17
