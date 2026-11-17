### Configuration Pitfalls & Resolution

- **HTTP 404/400 (Model ID/Endpoint Mismatches):** If OpenRouter returns 404 or 400 for a Gemini/Anthropic model, the model ID may be deprecated or misspelled. Check the [OpenRouter Model Registry](https://openrouter.ai/docs/models) for the exact model ID string. Avoid using generic aliases like `anthropic/claude-3.5-sonnet` if a versioned ID (e.g., `anthropic/claude-3-5-sonnet-20241022`) is required by the API.
- **HTTP 402 (Insufficient Credits):** When API calls fail with 402, the request size (max_tokens) may be too large for your remaining credit balance. Reduce `model.context_length` or add funds via the provider's dashboard.
- **Config Management:** Use `hermes config set section.key value` for persistent changes. For transient testing, override with CLI flags. Changes to config files require a session restart (`/reset` or re-invoking the command).
