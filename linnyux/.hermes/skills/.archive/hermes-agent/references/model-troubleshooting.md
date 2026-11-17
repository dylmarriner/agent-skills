# Model Troubleshooting

Common issues when configuring Hermes providers:

## HTTP 400 (Bad Request)
- **Cause:** Invalid model ID string or unsupported parameters.
- **Fix:** Verify the model ID string against the provider's registry. Do not use legacy IDs (like `-latest` suffixes if the provider doesn't support them). Check `hermes model` for the current valid list for your provider.

## HTTP 402 (Payment Required)
- **Cause:** Insufficient credits for the selected model.
- **Fix:** Add credits to your provider account (e.g., [OpenRouter Settings](https://openrouter.ai/settings/credits)).

## HTTP 404 (Not Found)
- **Cause:** The provider endpoint does not recognize the model string, or you are using the wrong base URL.
- **Fix:** 
    - Verify model string spelling.
    - Check that your `model.base_url` is correct for the specific provider (e.g., `https://openrouter.ai/api/v1` for OpenRouter).
    - If you are pointing to a custom proxy, ensure the model is served at the expected path.
