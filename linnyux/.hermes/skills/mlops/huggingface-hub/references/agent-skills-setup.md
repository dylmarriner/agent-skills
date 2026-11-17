# HF Agent Skills Setup Notes

## PIPX installation on PEP 668 systems

On Ubuntu 24.04+ (and other distros with PEP 668), system pip refuses to install packages globally.
Use pipx instead:

```bash
pipx install huggingface_hub
```

This installs `hf`, `huggingface-cli`, and `tiny-agents` into an isolated venv with symlinks in `~/.local/bin/`.

## Authentication

```bash
huggingface-cli login
```

Or set `HF_TOKEN` environment variable.

## Agent skill install commands

| Command | Scope |
|---|---|
| `hf skills add --global` | All projects, all agents |
| `hf skills add` | Current project only |
| `hf skills add --claude --global` | Claude Code, globally |
| `hf skills add --claude` | Claude Code, per-project |

## Claude Code plugin method

```
/plugin marketplace add huggingface/skills
/plugin install hf-cli@huggingface/skills
```

## Useful HF links

- Full CLI reference: https://huggingface.co/docs/huggingface_hub/guides/cli
- Token settings: https://huggingface.co/settings/tokens
- Jobs guide: https://huggingface.co/docs/huggingface_hub/guides/cli#hf-jobs
- Agents CLI docs: https://huggingface.co/docs/hub/en/agents-cli
