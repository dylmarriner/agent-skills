# Sourcing a stock calibration image (when the car is not attached)

Getting an OEM ROM/calibration image for an ECU you cannot read directly. The
living record of what has actually been found for this project — named sites,
URLs, prices, current hashes — is `docs/reverse_engineering/ROM_SOURCES.md` in the
repo. This file is the method; that file is the result.

## Order of preference

1. **Read it off the car.** Own calibration, free, and it settles the read-service
   question at the same time. `tools/rom_read.py`. Everything below is for when the
   adapter or the vehicle is not available.
2. **Mine the open-source tuning projects' definitions.** Free, already cloned, and often
   they hand you the flash recipe and the axis structure outright — see the last section.
   An engineer in this space wants map addresses and scalings more often than they want the
   OEM binary, and a definition file supplies those without owning copyrighted firmware.
3. **Buy the factory program file** for the exact software revision from a
   commercial ECU-file catalogue. Cheap, hashed, and the best provenance available.
4. Community forum dumps. Last resort — unverifiable revision and unknown provenance.

## The search key is the ECU software number, not the model

Read it off the ECU first: **DID `F188`** (`0xF188`, vehicleManufacturerECUSoftwareNumber,
`0x22 F1 88`) returns something like `L3CE-188K2-F`. **That string is the query.**

Searching by model and year returns marketing pages, tuning houses and car
listings. Searching the quoted software number returns the file catalogues,
because that is the key those catalogues index by. Quote it exactly, including
the revision letter:

```
"L3CE-188K2-F"            -> the file, if it exists
"L3CE-188K2"              -> every revision of that part number
```

Also read, and keep with the image: DID `F111` (a different revision here means the
ECU has been reflashed — relevant when picking which factory file to trust), `F112`/
`F113` (hardware/base part number) and `F806` (the ECU's own calibration checksum,
see the acceptance test).

**Match the exact revision.** A sibling revision of the same part number is not a
substitute: map addresses, axis definitions and the checksum target all differ. If
the catalogue only has `-A`..`-E` and your ECU reports `-F`, that is a different
tuning target, not a near-enough match.

## Catalogue classes, and what each actually holds

| class | what it is | what it holds for this work |
|---|---|---|
| ECU-file shops (paid, per file, credit bundles) | original **factory program files** for a named software number | the real thing: the OEM calibration, sourced from the dealer tool, hashed, with the container format and target address on the listing |
| Chiptuning file services | original + modified files, mostly popular diesel/petrol | OEM files exist but listings often name the engine, not the software revision — verify before paying |
| Generic ECU dump sites | workshop dumps, chiefly Bosch EDC15/16/17 | mostly wrong ECU family; check the manufacturer filter before believing a hit |
| Manufacturer/forum communities | people sharing files for a specific tuning tool | occasionally the only source; provenance and revision unverifiable until you have the bytes |

**Check the ECU manufacturer distribution before searching.** These catalogues are
dominated by Bosch (thousands of entries); Denso appears on the order of tens. A
Mazda DISI is a small corner of that market, so a "no results" on a big catalogue
means the ECU family is under-represented there, not that the file does not exist.

## Provenance ranking

A file a vendor describes as the **program file the manufacturer's diagnostic tool
loads** is strictly better than a workshop dump: it contains no other vehicle's
immobiliser, VIN or configuration data, and it is a defined revision rather than
whatever was in somebody's car. Prefer it even at a small cost. Buy one credit
rather than a bundle on a first purchase.

## The file is usually a container, not a flat ROM

VBF (and similar vendor flash formats) is a **container**: a header, metadata, the
target module address and the program payload. It is not a raw image the checksum or
map-scanning code can consume — unpacking it is a small RE task of its own. Useful
signals that you have a well-formed one: the listing states a format version, a type,
a module and an address, and its internal checksums reconcile with its header.

The **SBL is typically not included** in these files. That matters for flashing, not
for deriving map or checksum definitions.

## Acceptance test for ANY image

1. Unpack to a flat image and record size + SHA-256.
2. **The image must reproduce the ECU's own reported calibration checksum** — read
   `F806` off the car first (`0x22 F8 06`, or OBD mode 09 infotype 06). That single
   value converts the checksum search from "find something that validates" into
   "find the one that produces this number", which is a verification rather than a
   hunt.
3. Record the full identifier block from the ECU next to the image. An image without
   a hash and a provenance note is not a finding.

## Verifying a listing before buying

Catalogue pages are JS-rendered shops, so read the page itself rather than trusting a
search-result snippet. With `browser_exec`: navigate to the product URL, then
`js('document.body.innerText')` for the full text, or search the site index with
`?s=<software-number>&post_type=product` and read the result count — useful for
confirming whether all revisions exist (`MOSTRANDO LOS 6 RESULTADOS`). If
`web_extract` returns a search-only-backend error, `browser_exec` is the working
reader.

What to extract from the listing before paying: exact software number and revision,
container format and version, target module address, file size, published hash, and
whether the SBL is included.

## Ruled out: onion space

Checked properly, then stopped. Recorded with the working technique so the route is not
re-walked, and so the *transport* findings are available for other work.

**Reaching onion space** (this part works and is worth keeping):

* `torsocks` cannot resolve `.onion` — it resolves the name locally and fails *fast*, even
  for long-stable services. Skip it and hand the hostname to SOCKS instead:
  `curl --socks5-hostname 127.0.0.1:9050 -A 'Mozilla/5.0' <http://<addr>.onion>/`
* Confirm egress before trusting anything: `torsocks curl -s https://check.torproject.org/api/ip`
  must return `{"IsTor":true,…}` with an IP that is not yours. Corroborate independently through
  Tor's own directory API — `https://onionoo.torproject.org/details?search=<exit-ip>` returns the
  relay with an `Exit` flag. A different exit IP on each run means fresh circuits.
* Live onion addresses come from a directory (`dark.fail`, `tor.taxi`), **never from memory** —
  a stale address is indistinguishable from a dead service, and guessing wastes the session.

**Why it dead-ends for calibration files:**

* Ahmia, the main general index, is **JavaScript-only by its own admission**. Its onion root
  carries no `<script>` and no discoverable API, so a curl-based search is impossible.
* DuckDuckGo's onion *does* serve a no-JS `/html/?q=` endpoint that returns real result text
  over Tor — but the page carries zero anchors and zero redirect parameters. Searchable, not
  link-extractable without a JS engine.
* Public SearXNG instances block Tor exit IPs. General onion search engines are few, and the
  ones that exist are mostly dead.
* Structurally: Tor carries content that needs **anonymity**. A factory calibration file needs
  none. It is absent from the indexed web for *licensing* reasons, not censorship, so there is
  no mechanism by which it would be on Tor and missing from the open web.

## Free definitions: mine the open-source tuning projects first

Open-source tuning projects ship **definition files** — the tables, axes, scalings and
flash recipe for a ROM ID — and those are usually free, public and already cloned into
`reference/`. They are the better first stop, because much of what you actually need
rom-size, flash region, session bytes, transfer modes, axis structure — is in them, and
because a definition is data *about* a ROM rather than the OEM binary itself.

Find one for the **same engine**, not the same car. An engine family shares its map
structure across chassis and ECU generations, so a definition for the wrong generation
is still worth reading. LibreTuner keys definitions per ROM ID under
`ui/resources/definitions/<platform>/` (`main.json` plus per-ROM-ID files, e.g.
`l38k.json`), and its `mx5_nc/` tree shows dozens of per-ROM-ID variants — that layout
is the pattern to look for in any of these projects.

What a definition file typically gives, and whether it survives a generation change:

| field | transfers across generations? |
|---|---|
| `romsize`, `flashregion` (offset + size) | yes — the memory map layout |
| `auth.*_sessionid` (e.g. `0x85` flash, `0x87` download) | yes — the session bytes VersaTuner-style vendor data never exposes |
| `auth.key` | yes — and a free extra confirmation of a seed→key secret |
| `transfer.*` (server id / download mode / flash mode) | yes — confirms which service the read path uses |
| axis definitions (name, min, increment, size, datatype) | yes — real units and scaling maths |
| table `address` / offsets | **no** — these are ROM-specific |

So take the map *structure*, the flash recipe and the session protocol from a
wrong-generation definition, and the addresses from your own read.

**Offsets are often in the strings, not in a field.** Auto-analysed definitions name
tables after the address they found (`anal_2d_15x12_0x342a0L_1`) and put the axis
pointers in a `description` (`X-Index: 0xffff4114L`), with no structured `address` key at
all. Parse the name and description; do not conclude the addresses are absent because the
field is.

**A published definition does not exist for every generation.** When the upstream tree
carries only some platforms, that is a signal the maintainers were still collecting
firmware — check the project's issue tracker and forum threads for a public request for
the version you want, because the maintainers are the people who need it and will often
share. Reverse-engineered secrets in particular travel this way.
