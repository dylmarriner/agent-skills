# Winlice Packer — Analysis Notes

Target: ChimeraInstaller.exe (Czech Euroserver Sro. — Samsung FRP tool)
Size: 15,162,256 bytes (15MB)
Packer: Winlice (confirmed)

## Detection Indicators

- **Sections**: `.winlice` + `.boot` present
- **Entry Point**: Inside `.boot` section (not `.text`)
- **Entropy**: 7.88-7.99 across all data sections
- **Imports**: Single import per DLL — Winlice stubs each API call
- **Compiler**: Visual Studio 2019+ (v14.29)
- **Timestamp**: 2026-05-22 19:02:38

## LZSS Decompression Stub

Located at `.boot` section offset 0x58:

```
0x58: e8 4b 01 00 00    call 0x1a8          ; init call
0x5d: 53                push ebx
0x5e: 89 e3             mov ebx, esp
0x60: 53                push ebx
0x61: 8b 73 08          mov esi, [ebx+8]     ; source ptr
0x64: 8b 7b 10          mov edi, [ebx+0x10]  ; dest ptr
0x67: fc                cld
0x68: b2 80             mov dl, 0x80         ; bit buffer
0x6a: 8a 06             mov al, byte [esi]   ; LZSS loop
```

Characterized by `adc`/`rcl` bit-manipulation instructions (Winlice LZSS variant).

## Unpacking Status

- **First stage (LZSS)**: Partially reversed. Python decompressor written, produces ~6.4MB at offset 0x1a8
- **Result**: Contains MZ header at 0x1f560 within decompressed data, but PE content is still scrambled
- **Second stage**: Requires Windows API calls at runtime (import resolution triggers further decryption)
- **Conclusion**: Full unpacking needs Windows VM with x64dbg + ScyllaHide to catch OEP after runtime decryption

## Related Tools (same packer pattern)

- DigitalLicenseManager.exe: K9 + LAx packed (string-patched to localhost)
- OctoplusSamsungNew.exe: TeK packed (.TeK1 obfuscated, .TeK3 AES-encrypted)
- Octoplus/Medusa: VMProtect 2.x (.vmp0/.vmp1 sections)
