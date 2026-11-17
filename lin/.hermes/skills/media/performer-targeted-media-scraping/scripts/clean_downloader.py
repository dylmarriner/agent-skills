#!/usr/bin/env python3
"""Clean parallel downloader for video_queue_final.txt.
Fallback downloader when url2video is unavailable. Reads the deduped queue,
downloads N files in parallel with retry-on-timeout (timeouts are NOT marked done)."""
import os
import subprocess
import threading

QUEUE = "/tmp/video_queue_final.txt"
DONE = "/tmp/video_done.txt"
OUTDIR = "/mnt/storage/videos"
YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
N = 4
TIMEOUT = 600

def load_queue():
    done = set()
    if os.path.exists(DONE):
        with open(DONE) as f:
            for line in f:
                line = line.strip()
                if line: done.add(line)
    items = []
    with open(QUEUE) as f:
        for line in f:
            line = line.strip()
            if line: items.append(line)
    return [x for x in items if x not in done]

def download(entry, results, lock):
    parts = entry.split("|", 2)
    if len(parts) < 3: return
    perf, site, url = parts
    outpat = f"{OUTDIR}/%(title).120s [%(id)s].%(ext)s"
    cmd = [YTDLP, "--impersonate", "chrome",
           "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
           "--merge-output-format", "mp4",
           "--downloader", "aria2c",
           "--downloader-args", "aria2c:-x16 -s16 -k10M",
           "--retries", "2", "--fragment-retries", "2",
           "--no-playlist", "--no-warnings",
           "-o", outpat, url]
    try:
        before = set(os.listdir(OUTDIR))
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        after = set(os.listdir(OUTDIR))
        new = after - before
        mp4s = [x for x in new if x.endswith(".mp4") and ".part" not in x]
        for x in new:
            if ".part" in x:
                try: os.remove(os.path.join(OUTDIR, x))
                except: pass
        with lock:
            if mp4s:
                sz = os.path.getsize(os.path.join(OUTDIR, mp4s[0]))
                print(f"  OK [{site}] {mp4s[0][:60]} ({sz>>20}MB)")
                results["ok"] += 1
            else:
                results["fail"] += 1
            with open(DONE, "a") as df:
                df.write(f"{entry}\n")
    except subprocess.TimeoutExpired:
        for x in os.listdir(OUTDIR):
            if x.endswith(".part"):
                try: os.remove(os.path.join(OUTDIR, x))
                except: pass
        with lock:
            print(f"  TIMEOUT {url[:50]}")
            results["to"] += 1
            # Do NOT mark timeouts as done — they will be retried
    except Exception:
        with lock:
            print(f"  ERR {url[:50]}")
            results["err"] += 1
            with open(DONE, "a") as df:
                df.write(f"{entry}\n")

def main():
    items = load_queue()
    print("=== CLEAN PARALLEL DOWNLOADER ===")
    print(f"Queue: {len(items)} URLs | {N} parallel | {TIMEOUT}s")
    if not items:
        print("empty")
        return
    results = {"ok":0,"fail":0,"to":0,"err":0}
    lock = threading.Lock()
    idx = 0
    while idx < len(items):
        batch = items[idx:idx+N]
        idx += N
        threads = []
        for e in batch:
            t = threading.Thread(target=download, args=(e, results, lock))
            t.start()
            threads.append(t)
        for t in threads: t.join()
        print(f"  [{idx}/{len(items)}] ok={results['ok']} fail={results['fail']} to={results['to']}")
    print("=== DONE ===")

if __name__ == "__main__":
    main()
