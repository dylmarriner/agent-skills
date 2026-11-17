# Qualcomm EDL (9008) on Motorola

## Detection

```bash
lsusb | grep -i 05c6      # 05c6:9008 = Qualcomm HS-USB QDLoader 9008
```

Watch for it rather than assuming, and remember the device drops off the fastboot bus entirely once it switches.

## Entry methods

**Software — `fastboot oem blankflash`.** This is Motorola's EDL entry; their abl has **no `oem edl`** (verify with `fastboot oem help` before assuming otherwise). While `securestate: oem_locked` this returns:

```
(bootloader) Command Restricted
FAILED (remote: '')
```

Same for `oem qcom-on` and `oem bp-tools-on`. So **the software route is closed on a locked bootloader** — which is precisely the case where EDL would be useful.

**Key combo.** Power fully off, hold **Volume Up + Volume Down**, then plug USB while holding. Documented as working on the SM6375 platform; behaviour is model-dependent, so try it before disassembling anything. If it lands in fastboot or Android instead, this abl doesn't wire that combo to EDL.

**Test points.** Short the EDL pad to ground with tweezers while plugging USB. This is the boot ROM, so it works regardless of bootloader state — but it needs the back cover off.

- Get the pinout for the exact board revision, not the model family name. Published diagrams for a given device are frequently low-resolution watermarked marketing images: good enough to find the right *region* of the board, not to pick the right pad among near-identical neighbours.
- Typical layout: a small pad in a lower corner of the board, near a wide edge connector and the RF shield can. One write-up marks a single pad to short to ground; others describe two adjacent pins to bridge. Confirm on the actual board.
- Don't hold the short longer than needed, and don't miss the pad — bridging an unrelated IC is a real risk.

**Exit EDL:** hold Power ~25s.

## Tooling

**Firehose programmer** — a board-specific ELF. Sources:
- `hoplik/Firehose-Finder` — `fh_collection/<id>/<device>.elf`
- Motorola's own, extractable from the blankflash package (`mirrors.lolinet.com/firmware/lenomola/<year>/<codename>/blankflash/`, unzip `singleimage.bin`)

A valid one is a statically-linked aarch64 ELF, roughly a few hundred KB (`file` confirms).

**The `edl` tool** — `bkerler/edl`. Setup traps that cost real time:

```bash
python3 -m venv venv                                  # CLEAN venv
./venv/bin/pip install --upgrade pip setuptools wheel
./venv/bin/pip install pyserial pyusb docopt-ng colorama lxml capstone pycryptodomex
```

- **Do not** create the venv with `--system-site-packages`. A contaminated interpreter makes the `docopt` sdist build fail with an opaque `ModuleNotFoundError` from the build subprocess.
- Install **`docopt-ng`**, not `docopt` — same importable module name (`docopt`), pure Python, no build step.
- The module `edl` imports is **`Cryptodome`**, which comes from **`pycryptodomex`**. Installing `pycryptodome` (which provides `Crypto`) does not satisfy it, and the missing-module warning persists while pip reports "already satisfied".
- Run `edl.py` as a script from the repo root so its `edlclient` package resolves.
- Needs root for raw USB access.

```bash
edl.py printgpt --loader=<programmer>.elf   # the go/no-go test
edl.py e <partition>
edl.py reset
```

## Expectation-setting

**EDL is not a shortcut around a locked bootloader.** Motorola ships a *restricted* programmer — enough to restore fastboot, not enough for arbitrary partition work. The reported failure mode on a locked Moto is: device detected at 9008, handshake OK, firehose loads, device configures, then `Failed to read GPT header`. **No GPT read means no partition writes** — so if `printgpt` fails, stop; the remaining partition operations will not work either.

Confirm the toggle/FRP problem can't be solved on the Android side before opening the phone.
