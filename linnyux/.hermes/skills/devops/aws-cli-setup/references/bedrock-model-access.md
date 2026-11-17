# Bedrock Model Access & Invocation

## Model Listing Works Immediately

After AWS creds are configured, `list-foundation-models` works without any additional setup:

```
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[].modelId' --output text
```

Returns the full catalog of available models in the region.

## Inference Profile Gotcha (critical)

Newer models (Claude Sonnet 4+, Nova 2, DeepSeek V3.2, etc.) require **inference profiles**, not direct model IDs.

**Exact error when you invoke a model ID directly:**

```
Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0
with on-demand throughput isn't supported. Retry your request
with the ID or ARN of an inference profile that contains this model.
```

**How to find the right inference profile:**

```
aws bedrock list-inference-profiles --region us-east-1 \
  --query 'inferenceProfileSummaries[].inferenceProfileId'
```

## Do NOT Run Invoke Tests Without Asking

Model invocations can incur costs even on tiny test prompts. The user may block or flag this.

**Correct workflow to verify Bedrock access:**
1. `list-foundation-models` — confirms API access works
2. `list-inference-profiles` — discovers how to invoke modern models
3. Only run `invoke-model` after explicit user approval

## Older Models (No Inference Profile Needed)

Models like `amazon.nova-pro-v1:0` (non-2) and older Anthropic models can sometimes be invoked directly. But always let the user decide whether to test-invoke.
