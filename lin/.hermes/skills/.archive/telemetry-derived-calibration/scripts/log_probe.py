#!/usr/bin/env python3
"""Probe a real log file: what channels exist, how well resolved they are, and which
derivations the data can legally support.

Run this FIRST on any new log set, before writing a derivation or trusting a table.
Stdlib only. Never fabricates a value: it reports what is there and what is not.

    python3 log_probe.py LOG [LOG ...]
"""
from __future__ import annotations

import csv
import gzip
import io
import re
import sys
from pathlib import Path

# ORDER MATTERS: specific patterns first. Real headers put "MAF Voltage (V)" before
# "Mass Airflow (g/s)" -- a substring rule would feed volts into an airflow model.
CHANNELS = (
    ("time",   r"^time\b|logtime|timestamp|^sec\b"),
    ("rpm",    r"\brpm\b|engine speed"),
    ("speed",  r"vehicle speed|^vss\b|^speed\b"),
    ("boost",  r"boost\b|manifold (absolute )?pressure|^map\b"),
    ("load",   r"calculated load|load act|engine load|^load\b"),
    ("pedal",  r"accel\.? *(pedal|ped)|accelerator pedal"),
    ("tps",    r"throttle (position|pos|angle|duty)|rel\.? throttle"),
    ("maf",    r"mass airflow|mass air flow|^maf\b(?!.*volt)"),
    ("iat",    r"intake temp|boost air temp|^iat\b|manifold air temp|charge temp"),
    ("ect",    r"coolant temp|^ect\b|engine coolant"),
    ("afr",    r"actual afr|^afr\b|^lambda\b"),
    ("spark",  r"spark adv|ignition timing|^spark\b|timing advance"),
    ("kr",     r"knock retard|^kr\b|^knock\b"),
    ("wgdc",   r"wastegate duty|^wgdc\b|^wastegate\b|boost control duty"),
    ("vvt",    r"intake valve adv|^vvt\b|intake cam|cam angle"),
    ("idc",    r"inj\.? duty|injector duty|^idc\b"),
    ("fuel_press", r"hpfp|fuel press|di fuel press"),
)


def normalise(header: str) -> str:
    h = header.strip().strip('"').lower()
    h = re.sub(r"\[[^\]]*\]", " ", h)          # drop bracketed units
    h = re.sub(r"\([^)]*\)", " ", h)            # drop "(RPM)", "(mph)", "(F)"
    h = h.replace("\ufffd", "").replace("\u00b0", "")
    return re.sub(r"\s+", " ", h).strip()


def canonical(header: str):
    h = normalise(header)
    if not h or h.startswith("ap info"):
        return None
    for canon, pattern in CHANNELS:
        if re.search(pattern, h):
            return canon
    return None


def read(path: Path):
    text = (gzip.open(path, "rt", encoding="utf-8", errors="replace").read()
            if path.suffix == ".gz"
            else path.read_text(encoding="utf-8", errors="replace"))
    rows = list(csv.reader(io.StringIO(text)))
    head_i = None
    for i, r in enumerate(rows[:10]):
        if sum(1 for c in r if canonical(c)) >= 3:
            head_i = i
            break
    if head_i is None:
        raise SystemExit(f"{path.name}: no log header found in the first 10 rows")
    header, body = rows[head_i], rows[head_i + 1:]
    chan, src = {}, {}
    for j, col in enumerate(header):
        c = canonical(col)
        if c is None or c in chan:
            continue
        vals = []
        for r in body:
            if j >= len(r):
                continue
            try:
                vals.append(float(r[j].strip().strip('"')))
            except ValueError:
                pass                              # real logs carry junk cells
        if len(vals) >= 5:
            chan[c] = vals
            src[c] = col
    return header, body, chan, src


def step(vals):
    """Smallest non-zero difference = the channel's resolution/quantisation."""
    d = [abs(b - a) for a, b in zip(vals, vals[1:]) if b != a]
    return min(d) if d else 0.0


def report(path: Path):
    header, body, chan, src = read(path)
    print(f"\n=== {path.name}  ({len(body)} rows, {len(chan)} channels) ===")
    rate = None
    if "time" in chan and len(chan["time"]) > 1:
        span = chan["time"][-1] - chan["time"][0]
        rate = (len(chan["time"]) - 1) / span if span > 0 else 0.0
        print(f"log rate: {rate:.1f} Hz over {span:.1f} s")
    for c, vals in sorted(chan.items()):
        print(f"  {c:11s} n={len(vals):5d} range {min(vals):9.2f}..{max(vals):9.2f} "
              f"step {step(vals):7.3f}  <- {src[c]!r}")

    need = {
        "ve":     ("rpm", "maf", "boost", "iat"),
        "boost":  ("rpm", "boost"),
        "fuel":   ("rpm", "afr"),
        "spark":  ("rpm", "spark"),
        "ratios": ("rpm", "speed"),
        "torque": ("rpm", "speed", "time"),
    }
    print("  supportable:")
    for name, req in need.items():
        missing = [r for r in req if r not in chan]
        if missing:
            print(f"    {name:8s} NO  - missing {missing}: log these channels")
        elif name == "torque" and (rate or 0) < 15:
            s = step(chan["speed"])
            print(f"    {name:8s} NO  - {rate:.1f} Hz with speed step {s} quantises "
                  f"acceleration to ~{s * rate:.1f} m/s2 per count; log at 20 Hz+")
        else:
            print(f"    {name:8s} yes")
    return chan


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for a in argv[1:]:
        p = Path(a)
        if not p.exists():
            print(f"{p}: not found", file=sys.stderr)
            continue
        try:
            report(p)
        except SystemExit as e:
            print(e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
