#!/bin/bash
# agentmemory startup wrapper — forces .env values into process environment
# regardless of parent env (workaround for dotenv not overriding existing vars).
# Usage: install to ~/.local/bin/agentmemory-start and run instead of plain `agentmemory`.

set -euo pipefail

ENV_FILE="${HOME}/.agentmemory/.env"
if [ -f "$ENV_FILE" ]; then
    cd "${HOME}/.agentmemory"
    set -a
    source .env
    set +a
fi

exec agentmemory "$@"
