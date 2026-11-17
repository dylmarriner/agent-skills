# Building llama-server from llama.cpp Source

## Requirements

- CMake 3.15+
- C++17 compiler (gcc/clang)
- `libgomp1` (OpenMP support)
- ~8GB disk space for build artifacts

## Build Commands

```bash
# Clone or copy source
cp -r /path/to/llama.cpp /tmp/llama.cpp && rm -rf /tmp/llama.cpp/build

# Configure
cd /tmp/llama.cpp && mkdir build && cd build
cmake .. -DLLAMA_BUILD_SERVER=ON -DCMAKE_BUILD_TYPE=Release

# Build (takes 2-5 minutes on 4 cores)
cmake --build . --target llama-server -j$(nproc)
```

## Output

- Binary: `build/bin/llama-server` (~9MB)
- Shared libs: `build/bin/libllama-common.so*`, `build/bin/libggml*.so*`, `build/bin/libmtmd.so*`

## SMB/CIFS Limitation

**Do not build on an SMB/CIFS mount.** The cmake build creates symbolic links for shared libraries (e.g. `libggml-base.so → libggml-base.so.0 → libggml-base.so.0.10.0`). CIFS mounts return "Operation not supported" when trying to create symlinks.

Always build on a local filesystem (`/tmp/`, home directory, ext4/XFS).

## Docker Packaging

### Base Image Choice

The compiled shared libraries link against GLIBC 2.38+, which is only available in:
- Ubuntu 24.04+ (GLIBC 2.39)
- Debian testing/unstable

**Do NOT use ubuntu:22.04** — it has GLIBC 2.35 and will fail with:
```
libc.so.6: version `GLIBC_2.38' not found
```

Use `ubuntu:24.04` as the base image.

### Copy All Libraries

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates
COPY *.so* /usr/local/lib/
RUN ldconfig /usr/local/lib/
COPY llama-server /usr/local/bin/
COPY model.gguf /model.gguf
EXPOSE 11434
ENTRYPOINT ["llama-server", "-m", "/model.gguf", "--host", "0.0.0.0", "--port", "11434", "--embeddings", "--pooling", "mean"]
```

Copy ALL `.so*` files from `build/bin/` — the symlinks are needed for proper loading. cp handles this correctly on non-CIFS filesystems.

## Server Flags

| Flag | Purpose |
|------|---------|
| `-m /model.gguf` | Path to GGUF model |
| `--host 0.0.0.0` | Listen on all interfaces |
| `--port 11434` | Server port |
| `--embeddings` | Enable embeddings endpoint |
| `--pooling mean` | Mean pooling for embeddings (required for nomic-embed) |
| `--api-key KEY` | Require auth for API calls |
| `-ngl N` | Number of GPU layers (default: 0 = CPU only) |

## Verifying Embeddings

```bash
curl -s http://localhost:11434/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed","input":"hello world"}' | python3 -c "
import json,sys; d=json.load(sys.stdin); 
print('Dims:', len(d['data'][0]['embedding']))
"
```
