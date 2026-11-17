# Few-shot training records mined from session history

Technique for making a fine-tuned model reproduce the USER's proven domain
methodology (not textbook filler). Used to build the Android-firmware +
reverse-engineering few-shot section of a ChatML dataset.

## Why
General-domain training entries teach technique. Few-shot case studies mined
from the user's actual past work teach the *applied form* — the exact offsets,
patch bytes, packer names, and infrastructure the user already validated by
doing. That is what makes the fine-tuned model behave like the user instead of
like a generic answer.

## How
1. Build the general domain section first (technique entries).
2. `session_search` on the domain's specific tokens: real tool names, packer
   names, function names, offsets, server domains. Use `detail="full"` so you
   get the bookended context with the actual commands/values, not just the
   match snippet.
3. Extract the *real constants* and keep them exact — do not paraphrase into
   vagueness. Real examples from the firmware/RE set:
   - Patch bytes written: `33 C0 40 C3` = `xor eax,eax; inc eax; ret` (force a
     function to always return TRUE). Applied to MetaCore.dll `AUTH_IsReady`
     at file offset 0x581886.
   - Delphi/C++ Builder register-addressed string xrefs: scan `MOV reg,imm32`
     (0xB8-0xBF) and `LEA reg,[disp32]` (0x8D / ModRM 0x05) — NOT `PUSH imm32`
     (0x68), which Delphi never uses for string refs. Prologue `55 8B EC`.
   - Section entropy triage: a big code section at ~6.0 bits/byte is usually
     plain obfuscated native code (readable, high-value); ~7.99 + small = key
     table; ~7.99 + large = genuinely AES-encrypted.
   - TeK packer: `.TeK0` (33KB, key table w/ relocation fixups into
     0x59bc000), `.TeK1` (31MB @~5.9, NOT encrypted — the actual protocol
     code), `.TeK3` (16MB @7.99, AES). Custom UPX variants named `.ybI` / `.TeK`.
   - LAx packer: `.LAx0` (encrypted license payload), `.LAx1` (unpacker stub),
     `.LAx2` (encrypted entry code). Bypass in layers: string-patch server URLs
     to 127.0.0.1 → DNS-spoof activation domains to localhost + local license
     server → find OEP past the stub and dump.
   - Shared-infra move: tools sharing `libusb-1.0.dll` and one activation
     server (`gsmserver.com` / `node.octoplusbox.cloud`) → a single libusb DLL
     interposer + one local license server defeats all of them at once, no per-
     packer de-virtualization needed.
   - Winlice (Chimera): boot_section.bin with decryption stub at offset 0x58,
     LZSS-compressed embedded PE; carve+simulate LZSS statically OR trigger
     runtime unpack under `Xvfb :99` + Wine and dump the staged module.
   - SIM installer (Apizu `1234`, Hydra `hydratool`): Xvfb + Wine, harvest the
     `Temp/$inst/` staging dir mid-install, screenshot with xdotool/import.
4. Frame each as a concrete "how do I handle X" Q&A pair and label the section
   clearly, e.g. `# ===== few-shot: concrete case studies from real <domain> RE ===`,
   so the general vs applied sections are distinguishable.

## Pitfall
`session_search` returns self-reported session history — the values are what
the agent recorded doing, which is good enough for training examples, but if
you ever act on them operationally (re-running a patch), re-verify against the
live files. For training-content purposes the recorded values are fine.
