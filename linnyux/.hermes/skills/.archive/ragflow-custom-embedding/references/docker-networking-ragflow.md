# Docker Networking for RAGFlow + Custom Services

## The Problem

When running a custom service (like llama-server with embeddings) alongside RAGFlow's Docker stack, containers on different Docker networks can't reach each other — and the host may also be unreachable depending on firewall rules.

## RAGFlow's Network

RAGFlow creates a custom bridge network (typically `docker_ragflow`):

```bash
docker network ls | grep ragflow
# b6c824523874   docker_ragflow  bridge  local
```

Containers on this network get IPs in the `172.22.0.x` range.

## Option 1: Add your service to the same network (recommended)

```bash
docker run -d --name my-service --network docker_ragflow my-image
```

Containers can reach each other by container name:
- RAGFlow container name: `docker-ragflow-cpu-1`
- Your service: accessible at `http://my-service:PORT`

## Option 2: host.docker.internal (Linux caveats)

Docker Compose v2 supports `extra_hosts`:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

On Linux, `host.docker.internal` resolves to the **docker0 bridge gateway** (`172.17.0.1`), which may NOT be reachable from custom compose networks. The RAGFlow container is on `172.22.0.x`, not `172.17.0.x`.

If you need the host to be reachable, use the host's LAN IP or try a UFW route allow:

```bash
sudo ufw route allow proto tcp from any to any port 11434
```

## Option 3: Put service on host network

```bash
docker run --network host my-service
```

This exposes ports directly on the host — the service is reachable at `localhost:PORT` from the host, but NOT from Docker containers on bridge networks (unless UFW allows it).

## UFW Default Deny (routed)

Ubuntu's UFW has `Default: deny (routed)` by default, which blocks traffic between Docker networks and the host. Symptoms:
- Containers on one network can't reach containers on another
- Containers can't reach the host's IP on LAN interfaces
- `host.docker.internal` may be unreachable

Fix: add UFW route allow rules, or (better) put all communicating services on the same Docker network.
