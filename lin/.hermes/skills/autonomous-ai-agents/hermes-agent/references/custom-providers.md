---
name: hermes-custom-providers
description: "Add OpenAI-compatible API providers not built into Hermes (Mistral, Groq, Together, etc.)"
version: 1.0.0
---

# Hermes Custom Providers

How to add an OpenAI-compatible provider (Mistral, Groq, Together AI, Fireworks, etc.) that isn't in the built-in list.

## Named custom providers (current Hermes)

New named endpoints belong in the `providers:` mapping. The old `custom_providers:` list remains compatible for existing configurations, but do not use it for new entries.

Add one mapping entry without replacing the existing provider map:

```bash
hermes config set --force providers.<name> '{"api":"http://127.0.0.1:18192/v1","transport":"chat_completions","key_env":"MY_PROVIDER_KEY","default_model":"model-id","models":["model-id"],"context_length":262144}'
```

For a key already stored in a protected local file, use the supported `key_cmd` field instead of copying the secret into YAML or `.env`:

```yaml
providers:
  remote-gpu:
    api: http://127.0.0.1:18192/v1
    key_cmd: cat /path/to/protected/provider-key
    transport: chat_completions
    default_model: model-id
    models: [model-id]
    context_length: 262144
```

The helper must print only the token. Keep the model ID exactly as returned by `/v1/models`. Use `discover_models: false` only when deliberately pinning a configured `models` allowlist; otherwise let Hermes discover the catalog. Do not hand-edit model cache files unless an observed cache failure requires diagnosis.

## Select and verify a named provider

Use the provider's actual mapping name, not `custom:<name>`, and put provider/model flags after the `chat` subcommand:

```bash
hermes chat -q "Say exactly: working" --provider <name> --model <model-id>
```

Test a named route explicitly before changing `model.provider` or `model.default`; preserve the current default unless the user asks to switch it. Verify authenticated model discovery and a tiny completion through Hermes so the test covers both provider selection and authentication.

### API key prefix gotcha

Some providers (Venice, etc.) require the full key string INCLUDING any prefix as the Bearer token. For example, a key like `VENICE_ADMIN_KEY_aogCxFWODj5...` must be stored in `api_key` exactly as-is — the `VENICE_ADMIN_KEY_` prefix is part of the token, not a label to strip. If the API returns "Authentication failed", try the full string including the prefix.

## Remote GPU Backends

Use the remote host's native supervisor/onstart mechanism for the model process and a persistent local SSH tunnel for client access. Bind `llama-server` to remote loopback; forward it to a local loopback port with a user systemd unit (`Restart=always`, `WantedBy=default.target`). This avoids exposing an unauthenticated or API-key-protected model port to the public network.

Configure a named Hermes provider at the local tunnel URL (`http://127.0.0.1:<local-port>/v1`). Use `key_cmd` or `key_env` to resolve the protected credential at runtime when the remote server requires authentication; do not assume the key can be omitted. Set the model ID from the authenticated `/v1/models` response and configure context length only when supported by the deployed model/server.

Verify tunnel health, authenticated `/v1/models`, and one low-token Hermes chat using `--provider <actual-name> --model <model-id>`. Confirm the selected route with a successful response. Avoid long-context tests unless requested because they can consume substantial GPU time and cost.

A remote deployment is restart-ready only after verifying both sides: the server supervisor starts from the container's actual boot hook, and the local tunnel unit is enabled and active. A running process or an onstart file alone is not proof of reboot persistence.
