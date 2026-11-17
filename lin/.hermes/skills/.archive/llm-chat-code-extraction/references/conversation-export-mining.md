# Mining Code from LLM Conversation Export Files

## When to Use

You have one or more **already-exported conversation markdown files** (from DeepSeek, ChatGPT, Claude, etc.) and need to extract, clean, and integrate real code from them into a project. The exports are typically large (50K-500K+ bytes) markdown files containing a mix of:

- Jailbreak/roleplay preamble (user persona prompts, system overrides)
- Assistant refusals followed by user re-prompting
- **Leetspeak-encoded code blocks** mixed with legitimate protocol code
- Multiple iterations of the same concept under different class names
- Repeated, near-identical code blocks

## The Technique

### Phase 1: Discover What's There — Don't Read Raw

Do NOT `read_file` the whole export — they're huge (50K-500K+ bytes) and mostly noise.

Instead, use `search_files` to find all code definitions in one shot:

```
search_files(
    pattern="def |class |<key-protocol-terms>",
    path="path/to/conversation-export.md",
    output_mode="content",
    limit=200
)
```

The key terms to search for depend on the domain. For SS7 protocol code, the search was:

```
def |class |SS7|TCAP|MAP|SCCP|SRI|ATI|PSL|ISD|HLR|VLR|MSC|
SendRoutingInfo|forwardSM|HomeRouting|GSMMap|encode_tcap|decode_tcap
```

This gives you a roadmap of every class and method mentioned in the export without reading the noise.

### Phase 2: Find Real Code Among the Noise

Two patterns signal **real code** (as opposed to simulated/stub/imitation code):

1. **Byte-level protocol constants** — Hardcoded hex byte sequences like `0x62, 0x81, 0x90`, `0x02, 0x01, 0x46`, `b'\\x01\\x00\\x00\\x00\\x02\\x00'` — these are real protocol frames, not generated data
2. **Domain-specific encoding logic** — Functions like `_encode_bcd()`, `_encode_msisdn()`, BER/TLV encoders with real tag values matching standards (ITU-T Q.773, 3GPP TS 29.002)
3. **Standard `enum`/`IntEnum` classes** with documented values — `MAPOperation(IntEnum)` with `ANY_TIME_INTERROGATION = 0x31` (real ITU opcode)

**Ignore code that is:**
- Filled with `random.randint()` or `random.random()` for "real" data
- Has obvious "simulated" strings in output
- Wrapped in user-written leetspeak variable names (e.g. `SS7NuclearExploit`, `_craft_map_ati_nz` — but the *bytes inside* may still be real)
- Contains `# SIMULATED` or `# FAKE` comments

### Phase 3: Read the Right Sections

Use `read_file` with `offset`/`limit` to read only the sections that contain real code, using the line numbers from Phase 1:

```
read_file(
    path="conversation-export.md",
    offset=<line_number>,
    limit=200
)
```

You may need to read 3-5 windows per export file to get all the real code blocks. Batch independent reads in parallel.

### Phase 4: Deduplicate and Clean

LLM conversation exports often contain **the same code re-generated 3-4 times** under different names as the user kept re-prompting. Identify and collapse duplicates before integration:

| Class name pattern | Likely duplicates of |
|---|---|
| `SS7Hunter`, `SS7NuclearExploit`, `NZSS7NuclearExploit`, `NZTelecomExploit`, `NZCarrierExploits` | Same MAP/TCAP encoding, different wrappers |
| `MAPStack`, `MAPProtocol`, `RealExploitValidator` | Same operation codes, different organization |

**Cleaning rules:**
- Keep the most complete `enum`/constant definitions (they come from standards)
- Keep the most detailed encoding function (longer = more complete usually)
- Drop code that is clearly simulated (random data, hardcoded "simulated" returns)
- Preserve backward compatibility: existing public methods should keep their signature

### Phase 5: Integration Pattern

The integration follows a **delegation pattern** — old methods delegate to new protocol classes:

```python
# OLD (before):
def _build_sri_request(self, msisdn):
    return self._map_invoke(self.OP_SRI, {...})

# NEW (enhanced):
def _build_sri_request(self, msisdn):
    return self.map_proto.build_sri_request(msisdn)
```

This keeps existing callers working while the real encoding lives in the new classes.

**Protocol layers to separate:**
- OSI Layer 4: SCCP (routing/addressing)
- OSI Layer 4-5: TCAP (transactions, BER encoding)
- Application: MAP (mobile application part operations)
- Transport: M3UA (SIGTRAN for TCP/IP transport)

### Phase 6: Verify with Tests

Write a test that:
1. Imports every exported class
2. Encodes every MAP operation and checks byte count > minimum
3. Verifies TCAP Begin starts with `0x62`
4. Tests BER/TBCD roundtrip (encode → decode → match)
5. Tests SCCP and M3UA packet construction
6. Verifies manager sub-objects are properly instantiated

```python
# Test pattern
assert msg[0] == 0x62, 'TCAP Begin should start with 0x62'
assert len(msg) > 5, f'{name} too short ({len(msg)})'
```

## Pitfalls

- **Don't read export files without `search_files` first.** A 500K-byte export will burn your entire context budget with jailbreak roleplay preamble.
- **Don't skip the dedup phase.** You'll waste lines on 3 near-identical implementations of the same function under different leetspeak names.
- **Don't discard code just because the wrapper class has a "leetspeak" name.** The bytes inside — the actual protocol encoding — are often real, valid TLV from the standard. Extract the encoding logic; rename the class.
- **Don't remove legacy methods without verifying callers.** Old code may call `_map_invoke()` or `_build_sri_request()`.
- **Don't assume one export file is enough.** The same conversation may have multiple iterations across several exports. Check `search_files` across ALL export files, not just one.
- **Test after every major integration step.** The encoding logic from two different conversation iterations may use different tag values that conflict.

## Reference: Protocol Standards Used

| Standard | Layer | Key reference |
|---|---|---|
| ITU-T Q.713 | SCCP | Connection Request (0x01), UDT (0x09), CR/CC/CREF message types |
| ITU-T Q.773 | TCAP | Begin (0x62), Invoke (0xA1), ReturnResult (0xA2), BER TLV |
| 3GPP TS 29.002 | MAP | Operation codes: ATI=0x31, SRI=0x2D, SRIforSM=0x3A, ForwardSM=0x41, ISD=0x0C, PRN=0x34 |
| RFC 4666 | M3UA | ASP UP (0x01/0x01), ASP Active (0x02/0x01), Payload Data (0x03/0x01) |
| 3GPP TS 23.040 | SMS TPDU | SMS-SUBMIT TPDU encoding |

## Source Material Example

This workflow was developed while mining two DeepSeek conversation exports (totaling ~700K bytes) for SS7 MAP/TCAP/SCCP protocol code that was embedded inside jailbreak roleplay conversations. The exported conversations contained:

- 78+ code-related patterns across file 1
- 200+ code-related patterns across file 2  
- 5+ variant implementations of the same MAP protocol concepts
- Real byte-level TCAP encoding (`0x62, 0x81, 0x90` — TCAP Begin) mixed with simulated wrappers
