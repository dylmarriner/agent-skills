#!/usr/bin/env python3
"""PE section extractor + entropy/diff for WinLicense-protected commercial-tool builds.

  report <exe>            section table w/ entropy, md5, raw offset
  dump   <exe> <outdir>   write each section's raw data to <outdir>
  diff   <exeA> <exeB>    per-index comparison (same/differs/absent/inserted)
  selftest                assert entropy endpoints + md5 sensitivity

Why this exists instead of hand-rolled struct offsets: on a WinLicense build the
section table is the ONLY static thing left. Everything else is encrypted in
place (code section entropy ~7.99) and .winlice has zero raw bytes by design.

WinLicense marks its virtualized region with a zero-raw-size section (typically
named .winlice) that can never be dumped from disk -- the code is only
materialised in memory by the Oreans hypervisor at runtime. dumpsz reading 0 for
that one is the protection working, not a parse bug.

Section INDEX is not stable across vendor builds: an update can insert a small
section mid-table and shift every later index. Compare by walking the table (as
diff does), never by index against an older dump set.
"""
import hashlib
import math
import os
import struct
import sys


def sections(path):
    d = open(path, "rb").read()
    if d[:2] != b"MZ":
        raise ValueError(f"{path}: not a PE (no MZ)")
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    if d[pe:pe + 4] != b"PE\0\0":
        raise ValueError(f"{path}: bad PE signature")
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    ep = struct.unpack_from("<I", d, pe + 40)[0]
    base = pe + 24 + optsz
    secs = []
    for i in range(nsec):
        o = base + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1") or f"<unnamed{i}>"
        vsize, vaddr, rsize, roff = struct.unpack_from("<IIII", d, o + 8)
        chars = struct.unpack_from("<I", d, o + 36)[0]
        raw = d[roff:roff + rsize] if rsize and roff else b""
        secs.append({
            "idx": i, "name": name, "vsize": vsize, "vaddr": vaddr,
            "rsize": rsize, "roff": roff, "chars": chars, "raw": raw,
            "entropy": entropy(raw), "md5": hashlib.md5(raw).hexdigest() if raw else None,
        })
    return {"path": path, "entry": ep, "nsec": nsec, "sections": secs,
            "file_md5": hashlib.md5(d).hexdigest(), "file_size": len(d)}


def entropy(b):
    """Shannon entropy in bits/byte, 0..8. ~8.0 = encrypted/compressed, <6 = code/data."""
    if not b:
        return None
    counts = [0] * 256
    for x in b:
        counts[x] += 1
    n = len(b)
    return -sum((c / n) * math.log2(c / n) for c in counts if c)


def report(path):
    info = sections(path)
    print(f"{os.path.basename(path)}  size={info['file_size']:,}  md5={info['file_md5']}  "
          f"entry={info['entry']:#x}  sections={info['nsec']}")
    print(f"  {'idx':>3} {'name':<12} {'vsize':>10} {'rsize':>10} {'raw_off':>10} "
          f"{'chars':>10} {'entropy':>8}  md5")
    for s in info["sections"]:
        e = f"{s['entropy']:.4f}" if s["entropy"] is not None else "-"
        m = s["md5"][:16] if s["md5"] else "-"
        print(f"  {s['idx']:>3} {s['name']:<12} {s['vsize']:>#10x} {s['rsize']:>#10x} "
              f"{s['roff']:>#10x} {s['chars']:>#10x} {e:>8}  {m}")
    return info


def dump(path, outdir):
    os.makedirs(outdir, exist_ok=True)
    info = sections(path)
    for s in info["sections"]:
        if not s["raw"]:
            print(f"  skip {s['name']}: 0 raw bytes (virtualized in memory only)")
            continue
        out = os.path.join(outdir, f"sec{s['idx']:02d}_{s['name'].strip('<>')}.bin")
        with open(out, "wb") as fh:
            fh.write(s["raw"])
        print(f"  wrote {out} ({len(s['raw']):,} bytes)")
    return info


def diff(pa, pb):
    a, b = sections(pa), sections(pb)
    print(f"A = {os.path.basename(pa)}  md5={a['file_md5']}")
    print(f"B = {os.path.basename(pb)}  md5={b['file_md5']}")
    print(f"  {'idx':>3} {'nameA':<12} {'nameB':<12} {'sizeA':>10} {'sizeB':>10}  verdict")
    n = max(a["nsec"], b["nsec"])
    changed = []
    for i in range(n):
        sa = a["sections"][i] if i < a["nsec"] else None
        sb = b["sections"][i] if i < b["nsec"] else None
        na, nb = (sa["name"] if sa else "-"), (sb["name"] if sb else "-")
        za = sa["rsize"] if sa else 0
        zb = sb["rsize"] if sb else 0
        if sa and sb and sa["md5"] == sb["md5"]:
            v = "IDENTICAL"
        elif sa and sb:
            v = f"DIFFERS (entropy {sa['entropy']:.2f} -> {sb['entropy']:.2f})" \
                if sa["entropy"] is not None and sb["entropy"] is not None else "DIFFERS"
            changed.append((sa["name"], za, zb))
        else:
            v = "only in A" if sa else "only in B"
            changed.append((na if sa else nb, za, zb))
        print(f"  {i:>3} {na:<12} {nb:<12} {za:>#10x} {zb:>#10x}  {v}")
    return changed


def signer(path):
    """Authenticode signer CN -- often the only readable identity in a WinLicense build."""
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    base = pe + 24
    off, size = struct.unpack_from("<II", d, base + 96 + 4 * 8)
    if not size:
        return None
    der = os.path.join("/tmp", "pe_cert.der")
    # skip the 8-byte WIN_CERTIFICATE header or openssl reports "wrong tag"
    with open(der, "wb") as fh:
        fh.write(d[off + 8:off + size])
    import subprocess
    r = subprocess.run(["openssl", "pkcs7", "-inform", "DER", "-in", der,
                        "-print_certs"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("subject="):
            print(line)
    return der


def _self_check():
    assert entropy(b"") is None
    assert entropy(bytes(4096)) == 0
    assert abs(entropy(bytes(range(256)) * 16) - 8.0) < 1e-9
    a = bytes(range(256))
    assert hashlib.md5(a).hexdigest() != hashlib.md5(a[:-1] + b"\xfe").hexdigest()
    print("self-check ok: entropy 0/8 endpoints + md5 sensitivity")


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] == "selftest":
        _self_check()
    elif argv[0] == "report":
        report(argv[1])
    elif argv[0] == "dump":
        dump(argv[1], argv[2])
    elif argv[0] == "diff":
        diff(argv[1], argv[2])
    elif argv[0] == "signer":
        signer(argv[1])
    else:
        print(__doc__)
        sys.exit(2)
