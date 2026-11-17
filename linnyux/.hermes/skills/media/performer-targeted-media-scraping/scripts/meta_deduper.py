#!/usr/bin/env python3
"""Cross-site title+time deduper for video queues.
Resolves all URLs via yt-dlp --dump-json, groups by normalized title,
keeps best site per group. Use after Phase 1 crawl, before Phase 2 download."""
import subprocess, json, os, re, time
from collections import defaultdict

QUEUE = "/tmp/video_queue_final.txt"
META_FILE = "/tmp/all_metadata.jsonl"
YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
BATCH_SIZE = 50  # 20-URL batches are ~6 URLs/min; 50-URL batches are ~30 URLs/min

SITE_RANK = {"pornhub":1,"spankbang":2,"xvideos":3,"xnxx":4,"redtube":5,
             "youporn":6,"eporner":7,"porntn":8,"tnaflix":9,"xhamster":10}

def normalize(t):
    s = t.lower()
    for k,v in [('4','a'),('3','e'),('1','i'),('0','o'),('5','s'),('7','t'),('8','b')]:
        s = s.replace(k, v)
    s = re.sub(r'[^a-z0-9\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()

items = []
with open(QUEUE) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        parts = line.split("|")
        items.append({"performer":parts[0],"site":parts[1],"url":"|".join(parts[2:])})

print(f"Resolving {len(items)} URLs in batches of {BATCH_SIZE}...")

meta = {}
already_meta = set()
if os.path.exists(META_FILE):
    with open(META_FILE) as f:
        for line in f:
            if not line.strip(): continue
            try:
                d = json.loads(line)
                u = d.get("webpage_url","") or d.get("original_url","")
                if u:
                    meta[u] = {"title":d.get("title",""),"duration":d.get("duration",0),
                               "site":d.get("extractor","").split(":")[0].split(".")[0]}
                    already_meta.add(u)
            except: pass
    print(f"  Already resolved: {len(already_meta)}")

batch = []
for i, item in enumerate(items):
    if item["url"] in already_meta: continue
    batch.append(item["url"])
    if len(batch) >= BATCH_SIZE:
        bf = f"/tmp/meta_batch_{i}.txt"
        with open(bf, "w") as f:
            for u in batch: f.write(u + "\n")
        try:
            r = subprocess.run(
                [YTDLP, "--impersonate","chrome","--dump-json","--skip-download",
                 "--no-warnings","-a", bf],
                capture_output=True, text=True, timeout=180)
            for line in r.stdout.strip().split("\n"):
                if not line: continue
                try:
                    d = json.loads(line)
                    u = d.get("webpage_url","") or d.get("original_url","")
                    if u:
                        meta[u] = {"title":d.get("title",""),"duration":d.get("duration",0),
                                   "site":d.get("extractor","").split(":")[0].split(".")[0]}
                except: pass
            print(f"  Batch {i//BATCH_SIZE+1}: +{len(batch)} -> {len(meta)} resolved")
        except subprocess.TimeoutExpired:
            print(f"  Batch {i//BATCH_SIZE+1}: TIMEOUT")
        except Exception as e:
            print(f"  Batch {i//BATCH_SIZE+1}: ERROR {e}")
        if os.path.exists(bf): os.remove(bf)
        batch = []
        time.sleep(1)

if batch:
    bf = "/tmp/meta_final_batch.txt"
    with open(bf, "w") as f:
        for u in batch: f.write(u + "\n")
    try:
        r = subprocess.run(
            [YTDLP, "--impersonate","chrome","--dump-json","--skip-download",
             "--no-warnings","-a", bf],
            capture_output=True, text=True, timeout=180)
        for line in r.stdout.strip().split("\n"):
            if not line: continue
            try:
                d = json.loads(line)
                u = d.get("webpage_url","") or d.get("original_url","")
                if u:
                    meta[u] = {"title":d.get("title",""),"duration":d.get("duration",0),
                               "site":d.get("extractor","").split(":")[0].split(".")[0]}
            except: pass
    except Exception as e:
        print(f"Final batch error: {e}")
    if os.path.exists(bf): os.remove(bf)

print(f"\nTotal resolved: {len(meta)}/{len(items)}")

groups = defaultdict(list)
for item in items:
    url = item["url"]
    m = meta.get(url)
    if m and m["title"]:
        key = normalize(m["title"])
    else:
        slug = url.split("/")[-1].replace("-"," ").replace("_"," ")
        slug = re.sub(r'[^a-z0-9\s]', '', slug.lower())
        key = slug
    groups[key].append(item)

total_dup_removed = 0
deduped = []
for key, entries in groups.items():
    if len(entries) == 1:
        deduped.append(entries[0])
    else:
        entries.sort(key=lambda e: SITE_RANK.get(e["site"], 99))
        deduped.append(entries[0])
        total_dup_removed += len(entries) - 1
        titles = []
        for e in entries:
            u = e["url"]
            t = meta.get(u,{}).get("title","?")
            s = meta.get(u,{}).get("duration",0)
            titles.append(f"{e['site']}:{t[:40]}({s}s)")
        print(f"  DUP({len(entries)}): {' vs '.join(titles[:3])}")
        if len(entries) > 3:
            print(f"    ...and {len(entries)-3} more")

print(f"\n=== RESULTS ===")
print(f"  Total URLs: {len(items)}")
print(f"  Cross-site dupes removed: {total_dup_removed}")
print(f"  Final deduped: {len(deduped)}")

with open("/tmp/video_queue_deduped_final.txt", "w") as f:
    for item in deduped:
        f.write(f"{item['performer']}|{item['site']}|{item['url']}\n")
print(f"\nWritten: /tmp/video_queue_deduped_final.txt ({len(deduped)} URLs)")
