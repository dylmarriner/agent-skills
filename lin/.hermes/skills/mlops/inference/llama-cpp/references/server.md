# Server Deployment Guide

Production deployment of llama.cpp server with OpenAI-compatible API.

## Direct from Hugging Face Hub

Prefer the model repo's local-app page first:

```text
https://huggingface.co/<repo>?local-app=llama.cpp
```

If the page shows an exact snippet, copy it. If not, use one of these forms:

```bash
# Choose a quant label directly from the Hub repo
llama-server -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q8_0
```

```bash
# Pin an exact GGUF file from the repo tree
llama-server \
    --hf-repo microsoft/Phi-3-mini-4k-instruct-gguf \
    --hf-file Phi-3-mini-4k-instruct-q4.gguf \
    -c 4096
```

Use the file-specific form when the repo has custom naming or when you already extracted the exact filename from the tree API.

## Server Modes

### llama-server

```bash
# Basic server
./llama-server \
    -m models/llama-2-7b-chat.Q4_K_M.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    -c 4096  # Context size

# With GPU acceleration
./llama-server \
    -m models/llama-2-70b.Q4_K_M.gguf \
    -ngl 40  # Offload 40 layers to GPU
```

## OpenAI-Compatible API

### Chat completions
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-2",
    "messages": [
      {"role": "system", "content": "You are helpful"},
      {"role": "user", "content": "Hello"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Streaming
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-2",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

## Docker Deployment

**Dockerfile**:
```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y git build-essential
RUN git clone https://github.com/ggerganov/llama.cpp
WORKDIR /llama.cpp
RUN make LLAMA_CUDA=1
COPY models/ /models/
EXPOSE 8080
CMD ["./llama-server", "-m", "/models/model.gguf", "--host", "0.0.0.0", "--port", "8080"]
```

**Run**:
```bash
docker run --gpus all -p 8080:8080 llama-cpp:latest
```

## Monitoring

```bash
# Server metrics endpoint
curl http://localhost:8080/metrics

# Health check
curl http://localhost:8080/health
```

**Metrics**:
- requests_total
- tokens_generated
- prompt_tokens
- completion_tokens
- kv_cache_tokens

## Remote GPU Through an SSH Tunnel

Keep the inference listener on remote loopback, then forward it to local loopback:

```bash
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \\
  -L 127.0.0.1:18192:127.0.0.1:8080 user@host
```

For persistent use, manage the tunnel with a user-level systemd unit (`Restart=always`, network-online dependency) and enable it. Configure the client with the local `/v1` URL, not the host's public IP. Keep the model API key in a protected file or secret store and use the client's supported key command/environment reference; never paste it into config or shell history.

For Vast instances, confirm the model server is supervised and that the container boot hook actually invokes the onstart script; a file merely existing is not proof that it runs. Test `/health`, authenticated `/v1/models`, and one tiny inference through the final client route. Avoid full-context tests unless requested because they can take minutes and accrue GPU charges.

Do not capture raw Vast CLI responses or `--explain` output in logs: instance metadata can include Jupyter tokens, and explain output can include the CLI Authorization bearer. Prefer narrow display columns or locally filter fields before printing.

## Load Balancing

**NGINX**:
```nginx
upstream llama_cpp {
    server llama1:8080;
    server llama2:8080;
}

server {
    location / {
        proxy_pass http://llama_cpp;
        proxy_read_timeout 300s;
    }
}
```

## Performance Tuning

**Parallel requests**:
```bash
./llama-server \
    -m model.gguf \
    -np 4  # 4 parallel slots
```

**Continuous batching**:
```bash
./llama-server \
    -m model.gguf \
    --cont-batching  # Enable continuous batching
```

**Context caching**:
```bash
./llama-server \
    -m model.gguf \
    --cache-prompt  # Cache processed prompts
```
