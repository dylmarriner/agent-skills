---
name: octoplus-metacore-patch-analysis
description: 'MetaCore.dll (13.5 MB PE32, Delphi/BCB) from Octoplus FRP v3.0.6.0: string offsets, xref locations, patch strategies, and code flow for bypassing CompareAllBBChipHWID and AUTH_IsReady checks.'
---

# Octoplus MetaCore.dll Patch Analysis

## File Discovery

MetaCore.dll is in the **FRP installer** only:
```
/home/kubuntux/Downloads/RE/extracted/install_octoplus_FRP_3.0.6.0/app/MetaCore.dll
```

The Samsung installer (`install_octoplus_samsung_5.1.2.2`) has MetaCore-level auth logic embedded inside packed/encrypted sections (`.ybI`, `.(:R`) of `OctoplusSamsung.exe` — no standalone DLL there.

## Binary Properties

| Property | Value |
|----------|-------|
| Size | 13,514,752 bytes (13.52 MB) |
| Type | PE32 DLL (GUI, Intel 80386) |
| Compiler | Borland/CodeGear Delphi (CryptoPP export table) |
| Image Base | `0x5000000` |
| Sections | `.text` (code, 8.6 MB), `.rdata` (strings/data, 2.6 MB), `.data`, `.rsrc`, `.reloc` |
| Packing | None — clean DLL, entropy 5.4–6.7 |
| Exports | 8000+ `META_*` functions (MediaTek protocol ops); `AUTH_*` are internal |

## Section Table

| # | Name | VAddr | VSize | RawPtr | RawSize |
|---|------|-------|-------|--------|---------|
| 0 | `.text` | `0x1000` | `0x832e4a` | `0x400` | `0x833000` |
| 1 | `.rdata` | `0x834000` | `0x2742c0` | `0x833400` | `0x274400` |
| 2 | `.data` | `0xaa9000` | `0x1b1e50` | `0xaa7800` | `0x17800` |
| 3 | `.rsrc` | `0xc5b000` | `0x20cadc` | `0xabf000` | `0x20cc00` |
| 4 | `.reloc` | `0xe68000` | `0xb9bba` | `0xccbc00` | `0xb9c00` |

## RVA ↔ File Offset

```python
def raw_to_rva(raw_off):
    sections = [
        (0x400, 0x833000, 0x1000),     # .text
        (0x833400, 0x274400, 0x834000), # .rdata
        (0xaa7800, 0x17800, 0xaa9000),  # .data
        (0xabf000, 0x20cc00, 0xc5b000), # .rsrc
        (0xccbc00, 0xb9c00, 0xe68000),  # .reloc
    ]
    for rawp, raws, vaddr in sections:
        if rawp <= raw_off < rawp + raws:
            return vaddr + (raw_off - rawp)
    return None
```

## Critical String Offsets

| String | File Offset | RVA | Section |
|--------|-------------|-----|---------|
| `(0x%08X): CompareAllBBChipHWID(): fail!` | `0x938274` | `0x938e74` | `.rdata` |
| `AUTH_IsReady():` | `0x90ce28` | `0x90da28` | `.rdata` |
| `customer name mismatch with AUTH file` | `0x91dfae` | `0x91ebae` | `.rdata` |
| `bbchip_name is NULL, skip H/W version check` | `0x91d4d7` | `0x91e0d7` | `.rdata` |
| `AUTH_HANDLE::IsReady` | `0x919c04` | `0x91a804` | `.rdata` |

## Xref Discovery

### Method: Search for absolute memory address in .text

Delphi/BCB references strings by their full memory address (`image_base + RVA`). The 4-byte address appears as an immediate operand in:
- `PUSH <addr>` (`68 xx xx xx xx`)
- `MOV EAX, <addr>` (`B8 xx xx xx xx`)
- `MOV ECX, <addr>` (`B9 xx xx xx xx`)
- `MOV EDX, <addr>` (`BA xx xx xx xx`)
- `MOV [ESP+XX], <addr>` (`C7 44 24 XX xx xx xx xx`)

```python
IMAGE_BASE = 0x5000000
str_rva = raw_to_rva(string_file_offset)
str_mem = IMAGE_BASE + str_rva
ref_bytes = struct.pack('<I', str_mem)

# Search whole .text section
text_start, text_end = 0x400, 0x400 + 0x833000
off = text_start
while off < text_end:
    idx = data.find(ref_bytes, off, text_end)
    if idx < 0: break
    if idx > 0:
        p = data[idx-1]
        # Match: 0x68 (PUSH), 0xB8-0xBB (MOV reg), or C7 44 24 XX (MOV [ESP+XX])
        if p in (0x68, 0xB8, 0xB9, 0xBA, 0xBB):
            # Found xref
        elif idx >= 3 and data[idx-3:idx-1] == b'\xc7\x44':
            # Found MOV [ESP+XX] xref
    off = idx + 1
```

### Known Xrefs

| String | Xref Offset | Instruction | Notes |
|--------|-------------|-------------|-------|
| CompareAllBBChipHWID fail | **`0x6300ac`** | `PUSH` | Found via absolute addr search |
| AUTH_IsReady(): | **`0x581886`** | `PUSH` | Found via absolute addr search |
| AUTH_HANDLE::IsReady | **`0x5a8eb7`** | `MOV [ESP+24]` | Found via absolute addr search |
| bbchip_name skip | *not found* | — | No absolute addr in .text; may use RTTI/indirect table |
| customer name mismatch | *not found* | — | Same issue |

**Strings with no absolute-address xrefs** may be referenced through C++ `std::string` wrappers, VCL/RTTI metadata, or relative-to-a-base-table addressing. For these, use a disassembler (Ghidra/IDA) instead of byte-pattern search.

## Code Flow Analysis

### CompareAllBBChipHWID

The `PUSH` at `0x6300ac` pushes the fail format string. Search backwards for a conditional jump (`0x70`–`0x7F` range, 2-byte instructions) that controls execution:

```python
def find_jump_before(data, xref_offset, max_search=100):
    start = max(0, xref_offset - max_search)
    for off in range(xref_offset - 2, start, -1):
        if 0x70 <= data[off] <= 0x7F:
            delta = struct.unpack('<b', bytes([data[off+1]]))[0]
            target = off + 2 + delta
            if target > xref_offset + 4:
                return (off, data[off], delta, 'JUMP_OVER')
            elif target <= xref_offset:
                return (off, data[off], delta, 'JUMP_TO')
    return None
```

- `JUMP_OVER` = jump skips past the push (success path) → NOP the conditional to force fallthrough to success
- `JUMP_TO` = jump goes directly to failure code → convert to JMP (`EB`) to force jump over

### AUTH_IsReady

Search backwards from the xref for a function prologue (`55 8B EC` = `push ebp; mov ebp, esp`):

```python
def find_func_start(data, xref_offset, max_search=0x200):
    start = max(0, xref_offset - max_search)
    for off in range(xref_offset - 1, start, -1):
        if data[off] == 0x55 and data[off+1] == 0x8B and data[off+2] == 0xEC:
            return off
        if data[off] == 0x55 and data[off+1] == 0x89 and (data[off+2] & 0xF8) == 0xE0:
            return off
    return xref_offset
```

Patch: `33 C0 40 C3` (xor eax,eax; inc eax; ret) — 4 bytes, returns TRUE.

## Conditional Jump Opcode Reference

| Opcode | Instruction | Opcode | Instruction |
|--------|-------------|--------|-------------|
| `0x74` | JE / JZ | `0x75` | JNE / JNZ |
| `0x72` | JB / JNAE | `0x73` | JAE / JNB |
| `0x76` | JBE / JNA | `0x77` | JA / JNBE |
| `0x7C` | JL / JNGE | `0x7D` | JGE / JNL |
| `0x7E` | JLE / JNG | `0x7F` | JG / JNLE |
| `0x70` | JO | `0x71` | JNO |
| `0x78` | JS | `0x79` | JNS |
| `0x7A` | JP / JPE | `0x7B` | JNP / JPO |

All are 2 bytes: `opcode rel8`. Target = offset + 2 + rel8.

## Patch Script Evolution

| Version | What It Did | Shortcoming |
|---------|-------------|-------------|
| v1 | Found strings only | No xrefs, no patches applied |
| v2 | Added RVA/xref search for PUSH patterns | Missing MOV [ESP+xx] pattern, couldn't find bbchip_name/cust_name xrefs |
| v3 | Full code flow: cond jump backtrack + function prologue detection | Still can't find bbchip_name/cust_name via absolute addr |

## Pitfalls

- **MetaCore.dll location**: Not in Samsung installer! Always check all extracted installers from the same vendor.
- **RVA miscalculation**: Double-check: `RVA = section_vaddr + (file_offset - section_raw_ptr)`. First attempt used wrong RVA (0x938874 instead of 0x938e74).
- **bbchip_name / customer name**: These strings have no absolute-address xrefs in .text. They're likely referenced through an indirect string table or RTTI. Need a full disassembler to trace.
- **Calling convention**: `AUTH_IsReady` returns `BOOL` (int). Patch `xor eax,eax; inc eax; ret` for __cdecl, or `xor eax,eax; inc eax; retn 4` for __stdcall. Trying the wrong convention can crash the caller if it pops stack args.
- **Image base**: The DLL may be relocated at load time if ASLR is active. Delphi DLLs compiled without `DYNAMICBASE` use the declared image base. Check the DLL characteristics field in the PE header.
