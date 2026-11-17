---
name: claude-mcp-setup
description: Install, configure, and verify MCP servers for Claude Code, including direct server registration, gateway-based setups, and post-install validation.
---

# Claude MCP Setup

Use this skill when the user wants Claude Code MCP servers installed, configured, repaired, or verified.

## Scope

Covers:
- Claude Code `claude mcp add/remove/list`
- Direct stdio / http / sse server registration
- Gateway-based setups such as AIRIS MCP Gateway
- Optional helper frameworks such as SuperClaude
- Verification of final state in Claude Code, not just on disk

## Default workflow

1. Read the project or vendor install docs first.
2. Decide whether the user needs:
   - direct Claude MCP entries, or
   - a gateway bundle, or
   - both.
3. Install the servers or gateway.
4. Verify the config file Claude actually reads.
5. Run `claude mcp list` and confirm the servers are connected.
6. Report the exact connected entries and any remaining gaps.

## Important pitfall

Do not stop after installing a gateway bundle if the user asked to "install them all into Claude".

For this class of request, the gateway and the direct Claude MCP entries are separate deliverables. The gateway can be helpful, but the user may still want explicit Claude registrations for individual servers such as:
- context7
- sequential-thinking
- serena
- tavily
- magic / 21st.dev

If the user asked for "all of them", verify both:
- gateway health, and
- Claude Code MCP list coverage.

## Verification checklist

- `claude mcp list` shows the expected servers as connected
- `claude.json` / `.mcp.json` / gateway config files contain the expected entries
- any gateway service is actually up on localhost and healthy
- optional API-key-backed servers are present with the expected env wiring
- any helper framework install ends with a real verification command, not just a successful package install

## SuperClaude notes

SuperClaude installation is not the same thing as MCP server registration.

- `pipx install superclaude` installs the framework CLI
- `superclaude install` installs slash commands and agents
- `superclaude mcp ...` manages the AIRIS gateway bundle
- `claude mcp add ...` is still needed for direct Claude registrations when the user wants explicit servers

## AIRIS gateway notes

If using AIRIS MCP Gateway:
- make sure the gateway config file exists as a file, not a directory
- verify the gateway's API endpoint after startup
- if the gateway profile omits a server the user wants, add that server directly to Claude Code as well
- do not assume the recommended profile includes every desired optional backend

## One-line rule

For Claude MCP work, always prove the final Claude-side server list, not just the installer output.

## References

- See `references/airis-mcp-gateway-session.md` for the install/verification sequence and the gateway-vs-direct-registration pitfall.
