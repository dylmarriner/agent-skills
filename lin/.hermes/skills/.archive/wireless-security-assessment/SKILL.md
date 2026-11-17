---
name: wireless-security-assessment
description: Use when building or auditing WiFi pentest tooling.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [wireless, 802.11, pentest, aircrack-ng, hcxtools, hashcat, scope-enforcement]
    related_skills: [reverse-engineering, oss-forensics]
---

# Wireless (802.11) security assessment tooling

Scope: assessing or building tools that scan 802.11 networks, capture PMKID/EAPOL/WEP/WPS
material, recover PSKs offline, and report a wireless engagement on top of aircrack-ng,
hcxtools, hcxdumptool, hashcat and reaver/wash.

This is a class of task where **everything you remember about a flag set, a column order or a
hex offset is probably out of date**, and where a wrong guess fails silently: the tool exits,
the capture is empty, and the report says "target does not cache PMKIDs". Treat every
interface detail as something to re-verify against the installed binary before trusting it.

## When to Use

- Building or extending a WiFi assessment tool (scanner, capture engine, cracker front-end,
  engagement reporter) or reviewing one for correctness.
- Writing or debugging a parser for output this toolchain emits: airodump-ng CSV, wash table,
  reaver/bully progress, `hc22000`/`hashcat` material, `iw` output, 802.11 RSN/WSC elements.
- Constructing arguments for aircrack-ng / hcxdumptool / hashcat / reaver, or chasing a capture
  that "found nothing".
- Recovering and verifying a PSK or WEP key for a report, or deciding whether a captured
  handshake is a finding.
- Enforcing engagement scope (targets, channels, time window, frame/attempt budgets) on
  wireless attack code.

Not for: 802.11 driver/kernel work, Bluetooth/RFID, or pure PCAP forensics with no attack path.

## Order of work

1. **Probe before planning.** Find wireless interfaces and their capabilities, then ask each
   external tool what it supports: `ls /sys/class/net/*/wireless`, `iw dev`,
   `iw phy phyX info` (interface modes + channel inventory), `iw reg get`,
   `systemctl is-active NetworkManager wpa_supplicant`.
2. **Probe every tool's own help** before building an argv (`<tool> --help`, `-h`) and, for a
   reference decoder, its field tables (`tshark -G fields`, `tshark -G values`).
3. **Authorisation gate first.** Refuse to transmit without a signed scope file; validate
   strictly (authorised flag, signatory, targets, time window, budgets) and fail closed.
4. **Recon:** scan (`airodump-ng --output-format csv`) plus a beacon pass for the RSN AKM/PMF
   and WPS detail the CSV cannot express.
5. **Classify before attacking:** WPA2-PSK, WPA3-SAE, transition mode, OWE, Enterprise, WPA1,
   WEP, open; PMF capable/required. Classification decides the attack and rules out the
   impossible ones before any cracking time is spent.
6. **Capture** with the least invasive method that can work: PMKID (client-less) -> EAPOL
   (needs a client, and only if deauth is authorised) -> WPS -> WEP.
7. **Verify every recovered key yourself** (see `references/key-verification.md`) before it
   becomes a finding.
8. **Report** with per-finding CVSS vectors, evidence hashes, scope consumption (including
   refusals) and audit-chain status.

## Always-on rules

- **Build argv from the installed binary's advertised options, never from a version guess.**
  A flag the build does not know makes the tool exit without capturing, and the failure then
  looks like a property of the target instead of a tool error. Parse the help text once and
  construct the argument set from it. If a needed mechanism is absent (no target filter at
  all), proceed only with an explicit recorded fallback and post-filter the output.
- **Validate every parser against a reference implementation on identical bytes.** Build the
  input from the specification fields, decode it with your code *and* with a reference decoder
  (`tshark -V` / `-T fields`, the tool's own documented examples), and require agreement on
  every field. Your own fixtures encode your own wrong assumption and pass happily -
  cross-validation is the only thing that has caught real bugs in this class of work.
- **Never trust the cracker's word.** A potfile hit or `KEY FOUND` is a candidate: re-derive
  the PMK/PTK and recompute the captured PMKID or MIC. Report `verified` only on a match, and
  distinguish "primitive unavailable on this host" from "mismatch" - conflating them writes off
  a real compromise.
- **Scope is code, not intent.** Enforce allow/exclude lists, channels, time window and frame
  and attempt budgets in the one path every attack routes through, and record refusals (not
  just actions). Post-filter captures: targeting options such as `--filterlist_ap` /
  `--filtermode=2` affect *outgoing interaction only*, so out-of-scope hash material still
  lands in the file and must be discarded after conversion.
- **Make budgets bind inside the tool where it offers a cap** (`reaver -g <n>`,
  `aireplay-ng --deauth <n>`), and never let a tool transmit what you cannot count: pass
  `--disable_deauthentication` to hcxdumptool so only the counted deauth path emits
  deauthentication frames.
- **State limits instead of faking capability.** There is no offline dictionary attack against
  a correct SAE exchange; PMF-required defeats deauth-driven capture; a captured hash is not a
  compromise. Say so in the finding and move on.
- **Keep the repository's existing layout working.** Never delete, comment out or archive a
  legacy module to "clean up": replace its body with a real implementation, or alias it to the
  canonical module (`sys.modules[__name__] = importlib.import_module("pkg.real")`) so both
  import paths return the same object. This user requires zero stubs, zero mock data, zero
  TODOs/placeholders anywhere - grep for stub markers before declaring a task done.

## Pitfalls

- **Subprocess output races:** a tool that exits immediately (capture stopped with SIGINT,
  hashcat after an exhausted run) can still have lines in the pipe. Join the reader threads with
  a short timeout inside the snapshot method before parsing; a missing last line is a wrong
  parse, not an empty result.
- **WPS information element layout:** the beacon/probe-response WSC IE is a plain list of WSC
  data elements (`0x104A` Version first, then `0x1044` state, `0x1057` AP-setup-locked,
  `0x1053` selected-registrar config methods, ...). The fixed-offset layout belongs to the
  M1/M2 *message*, not the beacon IE - parsing the wrong one yields plausible nonsense (a
  garbage version, no lock state) rather than an error. Confirm any layout by dissecting a frame
  you built yourself with `tshark -V`.
- **hc22000 lines have no SNONCE field:**
  `WPA*02*MIC*MAC_AP*MAC_CLIENT*ESSID*NONCE_AP*EAPOL*MESSAGEPAIR` - the client nonce is inside
  the EAPOL blob (Key Nonce, offset 17) and the MIC at offset 81. A parser expecting a separate
  nonce field silently verifies garbage.
- **Crypto assertions need the spec's symmetry.** The PTK input is min/max-ordered over both the
  MAC pair and the nonce pair, so swapping either must NOT change the PTK - assert equality
  there and test sensitivity with a different key or nonce instead.
- **Published vectors can be mis-remembered.** Compute a NIST/RFC vector with an independent
  implementation before asserting it, and drop any you cannot confirm rather than shipping a
  wrong assertion.
- **Reference decoders may refuse fixtures in restricted directories** (permission error on a
  file the calling user owns). Write fixture captures into a world-readable temp dir (e.g.
  `/tmp`) or expose the directory through an env override.
- **A missing toolchain is not a broken tool:** install `aircrack-ng`, `hcxtools`,
  `hcxdumptool`, `hashcat`, `reaver`, `iw`, `tcpdump` (and `scapy`/`pycryptodome` for the
  Python-side decode/verify paths), then re-run the probe step. Never record a missing binary
  as a durable limitation.

## Supporting files

- `references/tool-dialects.md` - verified argv facts and output formats per tool (airodump-ng,
  wash/reaver/bully, hcxdumptool capability matrix, iw/airmon-ng, hashcat, tshark
  introspection).
- `references/key-verification.md` - PMK/PMKID/PTK derivations, MIC algorithm matrix, hc22000
  layout and frame offsets, WEP ICV check, what is not crackable.
- `scripts/build_beacon_pcap.py` - generates a real 802.11 beacon pcap from spec fields and
  prints the `tshark` commands that cross-check any decoder against the reference.
