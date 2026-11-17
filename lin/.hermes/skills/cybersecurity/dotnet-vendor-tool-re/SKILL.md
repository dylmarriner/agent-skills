---
name: dotnet-vendor-tool-re
description: Extract data and algorithms from obfuscated .NET tools.
version: 0.1.0
author: Hermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Dotnet, Reverse Engineering, Obfuscation, Decompilation, Vendor Tools]
---

# Managed Vendor Tool Reverse Engineering

Recover the data formats, algorithms and protocol layers of a commercial Windows
application that is managed (.NET) rather than native — decompile to C#, recover the
obfuscated string literals, and **run the vendor's own code in-process** instead of
reimplementing routines whose bodies live in a reflection-loaded module. This is for
managed assemblies only; for native packers (Themida, VMProtect, UPX variants) and
Delphi/Qt binaries use the sibling `commercial-tool-re` skill instead. Needs the
.NET SDK plus `ilspycmd`; everything else is stdlib.

## When to Use

- "Reverse engineer <vendor app>" where `file` reports `Mono/.Net assembly`.
- A vendor tool hides its strings — `search_files` for product terms finds nothing.
- You need a proprietary file format, licence format, or a definition/data package decoded.
- A recovered algorithm must be validated against a second implementation.
- You are about to reach for a disassembler on a .NET binary. Stop; decompile it first.

## Prerequisites

```bash
# .NET 8 SDK, user-local
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 8.0
export DOTNET_ROOT=$HOME/.dotnet; export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"
# ilspycmd MUST be version-pinned; the unversioned install fails with
# "DotnetToolSettings.xml was not found"
dotnet tool install -g ilspycmd --version 9.1.0.7988
```

- `MANAGED_APP_DIR` — the **installed product directory** (not a copy of one or two
  DLLs lifted out of it). Required for every in-process invocation; see Pitfalls.
- The product installed somewhere reachable. Wine prefixes under `~/Downloads/*/` are
  the usual shape on Linux; a Windows VM works too.

## How to Run

All scripts below are invoked through the `terminal` tool. The probe is a small .NET
project shipped with this skill — build it once, then call it per question:

```bash
cd <skill_dir>/scripts/managed_probe
dotnet build -c Release -v q --nologo
export MANAGED_APP_DIR=<installed product dir>
PROBE=bin/Release/net8.0/managed_probe.dll

dotnet $PROBE types      <asm.dll> "<substring>"
dotnet $PROBE resources  <asm.dll> <outdir>
dotnet $PROBE strings    <asm.dll> <tokens.txt> <out.tsv>
dotnet $PROBE find       <asm.dll> <ReturnType> <ParamType,...>   # static, by signature
dotnet $PROBE ctor       <asm.dll> <TypeFullName> <ArgType,...>  # internal types included
dotnet $PROBE invoke     <asm.dll> <TypeFullName> <method> <args...>
```

## Quick Reference

| need | do this |
|---|---|
| is it managed at all | `file <binary>` → `Mono/.Net assembly` |
| C# source | `ilspycmd -p -o <outdir> <asm>` |
| readable literals | `managed_probe strings <asm> <tokens.txt> <out.tsv>` |
| embedded blobs | `managed_probe resources <asm> <outdir>` |
| call an internal routine | `managed_probe invoke` / `ctor` / `find` |
| decode a vendor package | invoke the assembly's own codec by signature |
| licence/permission data | decrypt the licence file, read its XML |
| provenance | sha256 every artefact you cite |

## Procedure

**1. Confirm it is managed, then decompile — do not disassemble.**

```bash
file <asm.dll>          # "PE32 executable ... Intel i386 Mono/.Net assembly"
ilspycmd -p -o work/<AssemblyName>/decompiled <asm.dll>
```

The whole product becomes C#. Ghidra is the wrong tool and will cost a session.

**2. Recover the literals. `strings` will give nothing.**

Obfuscators move every literal into an encrypted manifest resource and replace each
use site with a call like `SomeClass._0008(-1478295536)`. Scrape the tokens out of the
decompiled C# and invoke the assembly's **own** decoder:

```bash
python3 - <<'PY'
import re, glob
pat = re.compile(r'[A-Za-z_0-9]+(?:_[0-9A-F]{4})*\._0008\((-?\d+)\)')
vals = set()
for f in glob.glob('work/**/decompiled/**/*.cs', recursive=True):
    vals.update(int(x) for x in pat.findall(open(f, encoding='utf-8', errors='ignore').read()))
# filter to large constants: small ints are arguments to unrelated overloads
open('work/tokens.txt','w').write('\n'.join(map(str, sorted(v for v in vals if abs(v) >= 100000))))
PY
dotnet $PROBE strings <asm.dll> work/tokens.txt work/strings.tsv
```

Then **resolve every token in place** while reading. Raw decompiled C# with
`_0008(-1478295536)` instead of `"MANIFEST"` is unreadable; rewrite the source with the
table before analysing it:

```bash
python3 - <<'PY'
import re, sys
table = dict(line.rstrip('\n').split('\t', 1) for line in open('work/strings.tsv') if '\t' in line)
for i, line in enumerate(open('work/Source.cs', encoding='utf-8', errors='replace'), 1):
    out = re.sub(r'[A-Za-z_0-9]+\._0008\((-?\d+)\)',
                 lambda m: '"%s"' % table.get(m.group(1), m.group(0)).replace('"', '\\"'), line.rstrip())
    print(f'{i}: {out.strip()}')
PY
```

**3. Identify things by signature, never by name.**

ILSpy invents `_XXXX` spellings for identifiers whose metadata names are non-printable
characters (e.g. `\x0e\x19\x05`). Name-based lookup against the real assembly fails
silently. Enumerate and match on signature:

```bash
dotnet $PROBE find <asm.dll> System.IO.Stream System.IO.Stream
dotnet $PROBE types <asm.dll> System.IO.Stream
```

**4. Inventory before decoding.** List data files beside the binary and the embedded
manifest resources (`managed_probe resources`). Data files usually beat the binary —
sort by size and look for anything that is clearly a table.

**5. Decode container formats structurally.** A very common shape is a ZIP whose
entries are stored (not deflated) plus a trailing signature, with a sidecar cache file:

```python
import zipfile
z = zipfile.ZipFile(path)
for i in z.infolist():
    print(i.filename, i.file_size, i.compress_type, hex(i.flag_bits))
```

Record entry counts across **all** samples, not one. Trailing fixed-size blocks
(`file[-256:]`) are signatures; verify by checking the container code reads
`file[0 .. len-256]`.

**6. Sweep an opaque payload cheaply, and write down what you ruled out.**

```python
import zlib, collections, math
ent = -sum(v/len(d)*math.log2(v/len(d)) for v in collections.Counter(d).values())
# ~8.0 = compressed or encrypted; 5-7 = structured records; <5 with text = unparsed plaintext
for off in range(0, 17):
    for tag, w in (("raw", -15), ("zlib", 15), ("gzip", 31)):
        try:
            o = zlib.decompressobj(w).decompress(d[off:])
            if len(o) > 500: print(tag, off, len(o), o[:6])
        except Exception: pass
```

No hit at any offset means the payload is **encrypted before compression** — static
decode is closed, and you should record that so the next session does not re-run it.

**7. Check the licence/permission artefact EARLY.**

Before concluding that data is missing or unobtainable, decrypt the licence and read
what the install was actually entitled to. A vendor tool that only downloads the part
of its data set the licence lists will look like a reverse-engineering failure when it
is a licensing fact. Decrypt with the key/IV recovered in step 2, look for a
`[signature][XML]` layout, and read the platform/feature lists.

**8. Prove a negative by executing the parser.**

When you suspect a data package is the wrong kind, do not argue from an element census
alone — instantiate every candidate parser against a real sample in-process and let the
vendor's own code answer:

```bash
dotnet $PROBE ctor <asm.dll> <Namespace.CandidateParser> System.IO.Stream
```

One throws, one succeeds. That is the finding.

**9. Cross-validate any recovered algorithm against a second implementation.**

If the vendor ships its own implementation of the routine, invoke it and diff against
your port over many inputs. Two independently written implementations agreeing
byte-for-byte is the strongest evidence available short of hardware truth — far
stronger than agreement with a reference clone. Then pin the vectors as a test.

**10. Leave self-tests and provenance.** Every tool you add gets
`--self-test`; every claim gets a `file:line` pointer or a byte offset plus a sha256
of the artefact. Record a ruled-out list — it is the highest-value part of the
document for whoever picks this up next.

## Pitfalls

- **A managed assembly loaded from bytes has no `.deps.json`** — its sibling DLLs are
  unresolvable by name and calls die on `FileNotFoundException` for whatever dependency
  that code path touches first. Fix with an `AssemblyLoadContext.Default.Resolving`
  probe against the installed product directory (the probe script does this from
  `MANAGED_APP_DIR`). Point it at the real install, not a folder of two copied DLLs.
- **`GetConstructors()` and `GetProperties(BindingFlags.Public)` find nothing useful.**
  The real members are `internal`. Use `BindingFlags.NonPublic` — otherwise reflection
  returns no candidate and you get a NullReferenceException at *your* call site that
  reads like a bug in the vendor's code.
- **Never `strings` a managed assembly and conclude it has no literals.** All of them
  live in the encrypted resource. Zero hits is expected.
- **Do not reimplement a routine that "isn't implemented in the assembly".** A method
  dispatching by name string to a reflection-loaded module is a dynamic proxy; its body
  only exists at runtime. Run it in-process rather than reverse-engineering it.
- **A `.zip` entry using an unsupported compression method is the encoder's library
  talking, not corruption.** `System.IO.Compression.ZipArchive` rejects
  LZMA/Deflate64/AES entries; use the compression library the product ships.
- **Filenames with non-printable characters.** ILSpy writes resource and type names
  literally; quote paths and expect mangling in tool output.
- **Do not fire network calls at a vendor API to enumerate what is downloadable.**
  Unguarded route probing 404s; the answer is in the licence file (step 7) or behind the
  app's own authenticated request shape.
- **Heap-dumping a running process needs the canary.** When falling back to scanning
  `/proc/<pid>/mem`, self-test the scanner against a marker string first, select the
  target by resident size (not by cmdline match — `pgrep -f app.exe` also matches your
  own wrapper), and treat a cold Wine prefix's minutes of `wineboot --init` as *retry*,
  not as a finding.

## Verification

```bash
# 1. the probe runs and can see types in the target assembly
dotnet $PROBE types <asm.dll> "" | head
# 2. literal recovery round-trips: pick any token, assert the known plaintext
python3 -c "
import sys
t = dict(l.rstrip().split(chr(9),1) for l in open('work/strings.tsv') if chr(9) in l)
assert t['-1478295536'] == 'MANIFEST', t.get('-1478295536')
print('string recovery ok')"
# 3. every tool you added has a passing self-test
<your_script> --self-test
# 4. every decoded sample validates as well-formed for its format
python3 -c "import glob,xml.etree.ElementTree as ET; [ET.parse(f) for f in glob.glob('out/*.xml')]; print('all parse')"
```

A session is not finished until the artefact inventory, the ruled-out list, and the
honest "not obtainable from here" list are all written down.
