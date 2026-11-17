#!/usr/bin/env python3
import json, logging, os, sys, urllib.request, urllib.error

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("memory-sync")

HERMES_HOME = os.path.expanduser("~/.hermes")
AGENT_ID = os.environ.get("NEXUS_AGENT_ID", "hermes")
DEVICE = os.environ.get("NEXUS_DEVICE", "default")
NEXUS_URL = os.environ.get("NEXUS_URL", "http://100.93.75.87:7777")
NEXUS_SECRET = os.environ.get("NEXUS_SECRET", "nexus-memory-shared-key-2026")
SEP = chr(167)  # section sign

MEMORY_FILE = os.path.join(HERMES_HOME, "memories/MEMORY.md")
USER_FILE = os.path.join(HERMES_HOME, "memories/USER.md")

def parse_entries(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        content = f.read().strip()
    if not content:
        return []
    return [e.strip() for e in content.split(SEP) if e.strip()]

def load_existing():
    existing = set()
    url = f"{NEXUS_URL}/v1/memory/profile/{AGENT_ID}"
    req = urllib.request.Request(url)
    req.add_header("X-Nexus-Secret", NEXUS_SECRET)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        for m in data.get("memories", []):
            existing.add(m.get("content", ""))
    except Exception:
        pass
    return existing

def sync_entry(content, mtype, importance=0.7):
    url = f"{NEXUS_URL}/v1/memory/save"
    payload = json.dumps({"agent_id": AGENT_ID, "content": content, "memory_type": mtype, "importance": importance, "metadata": {"device": DEVICE, "source": "hermes-local-sync"}}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Nexus-Secret", NEXUS_SECRET)
    try:
        urllib.request.urlopen(req, timeout=10)
        logger.info("Synced [%s]: %s", mtype, content[:60])
        return True
    except Exception as e:
        logger.error("Failed: %s", e)
        return False

def main():
    logger.info("Starting sync for %s", AGENT_ID)
    mem = parse_entries(MEMORY_FILE)
    usr = parse_entries(USER_FILE)
    if not mem and not usr:
        logger.info("No local entries to sync")
        return
    existing = load_existing()
    logger.info("Nexus has %d entries for %s", len(existing), AGENT_ID)
    n = 0
    for entry in mem:
        if entry not in existing:
            if sync_entry(entry, "observation", 0.7):
                n += 1
                existing.add(entry)
    for entry in usr:
        if entry not in existing:
            if sync_entry(entry, "preference", 0.8):
                n += 1
                existing.add(entry)
    logger.info("Sync complete: %d new entries", n)

if __name__ == "__main__":
    main()
