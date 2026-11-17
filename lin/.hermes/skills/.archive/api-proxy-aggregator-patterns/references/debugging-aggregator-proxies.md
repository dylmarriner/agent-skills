# Debugging API Aggregator Proxies

## Symptom: All providers show "configured: false"

**Root cause**: The `/health` endpoint showed 22 providers, all with `configured: false` despite `.env` having keys.

**Diagnosis steps**:
1. Check if `.env` file actually exists (not just `.env.example`)
2. Verify `require('dotenv').config()` is called before any provider initialization
3. Check `isConfigured()` logic:
   ```js
   isConfigured() { return !!this.apiKey && this.apiKey !== 'YOUR_API_KEY_HERE' && this.apiKey !== ''; }
   ```
   If `apiKey` is `undefined`, the env var isn't being read

## Symptom: All providers fail with model errors

**Root cause**: The `...body` spread overrides the resolved model ID.

**Error messages seen**:
- Groq: `The model 'unlimited-free-ai' does not exist`
- Together: `Unable to access model unlimited-free-ai`
- SambaNova: `The model 'unlimited-free-ai' does not exist`
- Cerebras: `Request failed: 404`
- Mistral: `Request failed: 400`
- NVIDIA: `Request failed: 404`
- Cohere: `Request failed: 405`

**Fix**: Change this:
```js
// BROKEN — ...body stomps model
return { model: getModelId(body.model), messages, ...body };
```
To this:
```js
// FIXED — explicit fields overwrite ...body
return { ...body, model: getModelId(body.model), messages };
```

## Symptom: Gemini returns "model not found"

**Root cause**: Experimental model IDs expire.

**Fix**: Update the model ID to a current stable name or hit the Gemini models list endpoint.

## Symptom: Cohere 405 (Method Not Allowed)

**Possible causes**:
- Wrong endpoint URL (Cohere uses `/v1/chat` not `/v1/chat/completions`)
- Wrong HTTP method (POST vs GET)
- API version mismatch

## Quick Verification

```bash
# Start the server
cd /path/to/project && node index.js &

# Health check
curl -s http://localhost:3000/health | jq '.activeProviders'

# Non-streaming request
curl -s http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unlimited-free-ai","messages":[{"role":"user","content":"Say hello"}]}'

# Streaming request
curl -s http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unlimited-free-ai","messages":[{"role":"user","content":"Say hello"}],"stream":true}' \
  | head -3

# Check server logs
curl -s http://localhost:3000/health | jq '.providers[] | select(.available==false) | {name, configured}'
```
