# MCP Troubleshooting & Credential Discovery

When working with MCP servers (like Hetzner Cloud) where credentials (HCLOUD_TOKEN) are missing from standard env files:

1. **Search across user infra**: Check secondary/remote machines (e.g., via SSH/Tailscale `kubuntux`) for existing IDE configs or Windsurf/Cline storage.
2. **Key locations for investigation**:
   - `~/.codeium/windsurf/mcp_config.json`
   - `~/.config/Windsurf/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
3. **Debugging Tip**: If an MCP server reports `ENOENT` (e.g., `mcp-hetzner-go`), check if the binary path is valid or if the tool is only available via npx/direct invocation.
4. **Integration**: Always ensure `/home/lin/.mcporter/mcporter.json` is updated to allow standard `mcporter` access if the global IDE config is fragmented.
