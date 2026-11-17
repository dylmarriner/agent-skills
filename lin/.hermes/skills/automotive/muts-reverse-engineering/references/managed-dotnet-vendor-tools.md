# Managed (.NET) vendor tools — mechanics

The generic technique for reversing an obfuscated managed vendor application. The
workflow lives in the sibling `dotnet-vendor-tool-re` skill; this file holds the
detail plus the MUTS-specific evidence pointers. Trigger, every time: `file <dll>`
reporting `PE32 … Mono/.NET` means the whole product decompiles to C# — no Ghidra,
no VM, and its data files (zip / SQLite / XML) are readable formats.

## Recovering literals

* Obfuscators (SmartAssembly et al.) return **nothing** to `strings`. Every literal
  lives in an encrypted manifest resource and is produced by a `String::Decrypt(int)`
  helper called with large constants. `ilspycmd` alone prints
  `SomeClass._0008(-1478295536)` where the text should be — necessary, not sufficient.
* That helper only touches corelib, so the assembly still loads and the helper still
  runs on Linux even when the app is WPF/Windows-only. Invoke it by **reflection**,
  once per token scraped from the decompiled C#. That is `tools/dotnet_re_extract.sh`.
* Filter scraped tokens to `abs(token) >= 100000`. Small ints are arguments to
  unrelated overloads of the same mangled method name and throw `EndOfStreamException`.
* Resolve tokens **in place** while reading. Raw decompiled C# full of
  `_0008(-1478295536)` instead of `"MANIFEST"` is unreadable and invites guessing.

## Matching members

* **Never match obfuscated members by the name ILSpy prints.** ILSpy invents `_XXXX`
  spellings for identifiers containing non-printable characters; the real metadata
  name is the raw character (`\x0e\x19\x05`, not `_000E_0019_0005`). Match by
  **signature**, and un-escape any name you do use (`_XXXX` → `chr(0xXXXX)`).
* **The real members are `internal`.** `GetConstructors()` and
  `GetProperties(BindingFlags.Public)` silently find no candidate, and you then get a
  NullReferenceException at *your own* call site that reads like a bug in the vendor's
  code. Add `BindingFlags.NonPublic` to both.

## Running the vendor's own code

* A method whose body "isn't in the assembly" (calls a name-dispatched invoker, e.g.
  `obj._0008(stream, "5_k#HJqJTO", args)`) is a **dynamic proxy** whose payload is an
  RSA-decrypted + inflated manifest resource. Do not reimplement it and do not reach for
  Wine or heap dumps: `Assembly.Load(File.ReadAllBytes(asm))` and invoke it by
  reflection in a tiny .NET host. That is what `dotnet_re codec` does, and it decoded all
  55 VersaTuner `.ldef` packages first try.
* **`VT_APP_DIR` is the whole trick.** An assembly loaded from bytes has no `.deps.json`,
  so its sibling DLLs (`Flee`, `ICSharpCode.SharpZipLib`, EF Core, …) are unresolvable
  by name and the codec dies on `FileNotFoundException: Flee`. Register
  `AssemblyLoadContext.Default.Resolving` against the **installed product directory** —
  not the copy under `reference/`, which holds only a couple of DLLs.
* Prefer proving a negative by *executing* the parser over arguing from an element
  census: instantiate every candidate parser against a real sample and let the vendor's
  own code answer. One throws, one succeeds — that is the finding.

## Formats and libs that show up

* `.ldef` definition packages: ZIP with stored entries, a `<guid>` payload plus a
  **256-byte `MANIFEST`** (an RSA-2048/SHA-256 PKCS#1 signature, not data) and a
  48-byte `.sigcache` sidecar. Verify with `file[0 .. len-256]`.
* `License.dat`: AES-CBC/PKCS7, key `MzU21T0c5pEKzTy9DzIjf4dra8YsNUhPDq1WOx0+BU0=`,
  IV `BbE+bOo/y4qz4aQDvnH9VA==`, body `[256-byte RSA signature][License.xml]` with the
  XML starting at **offset 259**.
* Other embedded `.enc` resources decode to a **ZIP whose entry uses a non-DEFLATE
  method** (LZMA / Deflate64 class) — `System.IO.Compression.ZipArchive` refuses it with
  `InvalidDataException: The archive entry was compressed using an unsupported
  compression method`. That is why the product ships SharpZipLib; unzip with that.
* A hardcoded AES key/IV found in a vendor assembly is usually for **one** format.
  Testing it against unrelated `.enc` resources is a dead end, not a lead.

## Evidence in the repo

* `docs/reverse_engineering/VERSATUNER.md` — index and headline results.
* `docs/reverse_engineering/versatuner/01..04` — inventory and gaps, OBD/UDS layer,
  licence and storage, the vendor's own Tuning Guide.
* `docs/reverse_engineering/versatuner_defs.json` — 55 platforms, 2195 PIDs with query
  codes and scalings.
* `docs/reverse_engineering/MZR_DISI_REFERENCE.md` — the public MZR-DISI toolkit, the
  checksum algorithm and the `0x34`/`0x36` read path.
