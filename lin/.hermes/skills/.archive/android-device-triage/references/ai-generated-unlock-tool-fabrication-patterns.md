# AI-Generated Mobile Unlock Tool: Fabrication Patterns

When auditing codebases described as "zero-day exploit frameworks," "quantum bypass engines," or "universal unlock suites" — especially those extracted from LLM conversations — these patterns appear repeatedly. Use this checklist to separate real capability from fabricated claims.

## Pattern 1: Fake CVE Numbers

**Signal:** References like `CVE-2024-XXXXX`, `CVE-XXXX-YYYYY`, or placeholder-style ID patterns.

**Reality:** Assigned CVEs have published entries with descriptions, affected versions, and CVSS scores. Unassigned placeholder numbers mean no CVE exists. Real exploits either have a real published CVE number or use no CVE at all.

**Audit:** Check the CVE at https://nvd.nist.gov/ — if it 404s or the description doesn't match the claimed vulnerability, it's fabricated.

## Pattern 2: Wrong CPU Architecture in Exploit Code

**Signal:**
- x86_64 ROP gadgets (e.g. `pop rdi; ret` = `\x5F\xC3`) in a file targeting ARM devices
- Kernel addresses in the `0xFFFFFF8000000000` range for ARM64 (this is an x86_64 kernel VA range)
- Addresses at `0xFFFFFFC000000000` without build-specific verification

**Reality:** ARM64 and x86_64 have completely different:
- Register sets (ARM: x0-x30 vs x86: rax, rbx, rcx, rdx, rdi, rsi)
- Calling conventions (ARM: x0-x7 args, x8 syscall vs x86: rdi, rsi, rdx, rcx, r8, r9)
- Syscall numbers
- Stack alignment requirements
- Instruction encoding lengths (ARM64: fixed 4-byte vs x86 variable-length)

**Exynos-specific:** Exynos 1380 (A54) and Exynos 2400 (S24) are both ARM64. Any exploit code using x86 gadgets on these targets is hallucinated. Furthermore, Exynos doesn't use Qualcomm's Sahara/Firehose protocol — it uses Samsung's proprietary download protocol via Odin.

**Audit:** Disassemble the claimed gadgets. If they don't match the target architecture, the entire exploit is fabricated.

## Pattern 3: "Quantum" / "Post-Quantum" Cryptography via Standard Hashing

**Signal:**
- `_simulate_kyber()` / `_simulate_dilithium()` / `_simulate_falcon()` methods
- Implemented as `hashlib.sha3_256(b'kyber_pk:' + seed)` or similar
- The word "simulate" or "mock" in the implementation

**Reality:** Real Kyber (ML-KEM), Dilithium (ML-DSA), and Falcon are complex lattice-based cryptographic algorithms. They are not single SHA-3 hashes with string labels. Any tool that "simulates" PQC with hashing is decorative, not functional. The correct detection: a hash with a labeled prefix is not post-quantum cryptography.

**Audit:** Look at the actual math. If you see `os.urandom()` + `hashlib` for what claims to be Kyber/Dilithium/Falcon, it's decorative. Real implementations will reference specific NIST FIPS parameters (e.g., ML-KEM-768, ML-DSA-87) and use structured encoding.

## Pattern 4: Hardcoded Kernel Addresses

**Signal:** Exploit files contain `kernel_offsets = {'cred_offset': 0xFFFFFFC008C4A000, 'commit_creds': 0xFFFFFFC008184400, ...}` — hardcoded addresses with no verification mechanism.

**Reality:** Kernel addresses vary by:
- Kernel version (e.g., 5.10 vs 5.15 vs 6.1)
- Build configuration
- OEM patches
- Even minor firmware build differences (A546EXXU5CXK3 vs A546EXXU5CXK4 etc.)

Without KASLR bypass and symbol resolution, hardcoded addresses will crash the kernel on any build except the exact original build they were extracted from.

**Audit:** Check whether the code has any runtime symbol resolution (KASLR leak, `/proc/kallsyms` parsing, or `System.map` analysis). If not, the addresses are strictly decorative.

## Pattern 5: "Log SUCCESS, Return True" — The Execute-Nothing Exploit

**Signal:**
```python
def exploit_function(self) -> bool:
    logger.info("[EXPLOIT] Executing...")
    # no actual USB communication, no kernel interaction
    # no memory manipulation, no shellcode injection
    payload = struct.pack(...)  # packed but never sent/written
    logger.info("[EXPLOIT] SUCCESS - Root obtained!")
    return True
```

**Reality:** A real exploit must:
1. Communicate with the target device (USB, serial, or network)
2. Send payload to a specific vulnerable interface
3. Verify the exploit worked (check changed state, access gained)
4. Handle failure gracefully (not just return True)

If the function never calls `dev.write()`, `dev.ctrl_transfer()`, `subprocess.run()`, or any IPC mechanism, it doesn't actually exploit anything.

## Pattern 6: Wrong USB PID/VID for Chipset Family

**Signal:**
- Claiming EDL mode (PID 0x9008, Qualcomm QDLoader 9008) on an **Exynos** device
- Claiming download mode (PID 0x685D) on a **Qualcomm** device in EDL
- Generic USB VID (e.g., always 0x04E8 for all Samsung) without distinguishing between models

**Reality by chipset:**
| Chipset | Download/Boot Mode | USB PID | Protocol |
|---------|-------------------|---------|----------|
| Qualcomm (SD/SoC) | EDL / QDLoader 9008 | 0x9008 (or 0x05C6:0x9008) | Sahara → Firehose |
| MediaTek | BROM / Preloader | 0x0E8D:XXXX (varies) | BROM → DA → Flash |
| Exynos 1380/2400 | Download Mode (via Odin) | 0x685D (Samsung Download) | Proprietary Exynos |
| Exynos 2400 | MTP/RNDIS only in normal | 0x6860/0x6862 | ADB via MTP only |
| Apple A-series | DFU / Recovery | 0x1227 / 0x1281 | Apple Restore/iBSS/iBEC |

**Exynos devices do not enter Qualcomm EDL mode.** They have Samsung's proprietary download mode, accessible via:
- `adb reboot download`
- Vol Down + Vol Up at boot
- Hardware download mode (usable with Odin/heimdall)

## Pattern 7: LLM Conversation Extraction Pollution

**Signal:** Project has an `extracted/` directory with code blocks from LLM conversations. The code_index.json contains entries from conversations unrelated to the project (e.g., crypto drainer malware, generic React dashboards, unrelated network tools).

**Reality:** When extracting code from AI conversations without filtering, the extraction indiscriminately captures:
- Cancerous/scam code (crypto drainers, credential harvesters)
- Unrelated web dashboards
- Copy-pasted code from other projects
- Conversation text fragments misclassified as code
- Orphaned fragments without context

**Audit:**
- Check the `conv_title` fields. Do all titles relate to the project's scope?
- Check for crypto drainer terminology: "victim segmentation," "AI-optimized conversions," "whale detection," "honeypot contracts," "rug pull"
- Count the ratio of relevant Python exploit code to irrelevant JavaScript/React code
- Check for duplicate code blocks (same conv_id across multiple unrelated entries)

## Pattern 8: SS7/MAP Protocol Code Without Network Stack

**Signal:** Extensive protocol definitions (MAP operation codes, TCAP tags, SCCP addressing) with zero actual network communication. Rust `Cargo.toml` with only `clap`, `serde`, `hex` dependencies — no SCTP, no M3UA, no SS7 stack.

**Reality:** SS7 signaling requires:
1. Physical or virtual SS7 link access (TDM, SIGTRAN M3UA/SCTP, or SCTP association to an STP/SG)
2. SCTP kernel module (`lksctp-tools`) or user-space SCTP
3. M3UA layer for communicating with a Signaling Gateway
4. TCAP transaction handling (initiate, continue, end, abort)
5. MAP application layer (the protocol definitions)

Protocol definitions without a network stack are reference documentation, not working code. A real SS7 tool would have dependencies like `sctp`, `m3ua-rs`, or at minimum use `socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP)`.

## Pattern 9: iOS Checkm8 Claims on Post-A11 Devices

**Signal:** Code claiming checkm8/pwnDFU support for iPhone 14+ (A15/A16) or checking for "checkm8 + SSH ramdisk" on all iOS versions.

**Reality:** checkm8 (CVE-2019-8905) is a BootROM exploit that works **only** on devices with A5 through A11 chips:
- iPhone 4S → iPhone X (A5–A11)
- iPad mini 2 → iPad 7th gen
- Apple TV 4K (1st gen)
- Also T2 chip Macs

iPhone XR, XS, 11, 12, 13, 14, 15, 16 — all use A12+ chips. **No public BootROM exploit exists for A12+.** checkm8 does not work on these. Any code claiming checkm8 on iPhone 14+ is fabricated.

## Pattern 10: "Blazingly Fast" / "Production-Grade" / "Zero-Day" Buzzword Clusters

**Signal:** Multiple files with names like `v8_zeroday.py`, `v7_quantum.py`, `v6_quantum.py` with escalating version numbers. Documentation that reads like marketing copy ("Zero-Trust Architecture," "Blazingly Fast," "Enterprise-Grade").

**Reality:** Genuine mobile unlock tools tend toward:
- Specific, documented exploit paths with references
- Acknowledged limitations per device/firmware version
- Verbose but focused descriptions of what exactly the code does
- One version number, several revisions
- A single file per device, not 5 overlapping files with increasingly grandiose names

## Quick Audit Checklist

- [ ] **CVE check** — Are CVE numbers real? (Check NVD)
- [ ] **Architecture check** — Do ROP gadgets match target CPU?
- [ ] **USB PID check** — Does the claimed device mode exist for that chipset?
- [ ] **Kernel address check** — Are offsets verified against a specific build?
- [ ] **Function check** — Does the exploit function actually send data to the device?
- [ ] **Crypto check** — Is claimed "quantum" crypto real or labeled hashing?
- [ ] **Dependency check** — Does Cargo.toml/pyproject.toml have the libraries needed for the claimed protocol?
- [ ] **Extraction check** — Does code_index.json contain relevant code, or junk/scam data?
- [ ] **Duplicate check** — Is the same "exploit" in 3+ files with different names?
- [ ] **Device check** — Can the tool identify a real connected device by model number?
