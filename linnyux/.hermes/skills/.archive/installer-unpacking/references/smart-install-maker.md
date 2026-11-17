# Smart Install Maker v5.04 Analysis

Reference for extracting files from Smart Install Maker installers — a format with no open-source extraction tool.

## File Structure

| Offset Range | Size | Content |
|---|---|---|
| `0x000000 - 0x05A200` | 389KB | PE32 executable (Delphi/Borland) — installer engine |
| `0x05A200 - 0x2044AA` | ~6.6MB | SIM overlay — metadata, file table, multilingual UI strings |
| `0x2044AA - 0x20454C` | 162B | Null padding |
| `0x20454C - 0x244DD5` | 264KB | RAR5 archive (may contain one file, often `adbsdm.exe`) |
| `0x244DD5 - EOF` | 206MB+ | **Encrypted** payload — all embedded files |

## SIM Overlay Format

The overlay at `0x05A200` begins with `Smart Install Maker v. 5.04` and contains null-separated fields:

### Header Fields (sequential)

```
[0]:   "Smart Install Maker v. 5.04"
[1-2]: "0", "0" (version numbers)
[3]:   "1" 
[4]:   "4369121" (CRC or internal ID)
[8]:   "Welcome to installer <AppName>"
[9]:   "Copyright ..."
[21]:  "disk@$&%19.pak"  ← PAK file reference
[22]:  "1"
[23]:  "415234798" (PAK size when extracted to disk)
[26]:  "25" (number of files)
[28]:  "Apizu Tool" (application name)
[35]:  "4.4.4" (version)
[36]:  "1"
[37]:  "https://..." (URL)
```

### File Entries

The `@$&%` encoding prefixes indicate entry types:
- `@$&%04\filename` — Regular file entry
- `@$&%01\name` — Shortcut/group entry
- `@$&%19.pak` — Disk-based PAK archive

Each file entry is followed by metadata fields:
```
path, [size], type_flag, subtype_flag, count
```

Example entries:
```
@$&%04\Apizu Tool.exe   → ['1', '0', '1']        # type=1, sub=0, count=1
@$&%04\READ ME.txt      → ['405683', '1', '0', '1']  # size=405683, type=1, sub=0
@$&%01\Apizu Tool       → ['0', '6592464', '0', 'Windows 95/98...']  # group, 6592464=total size
@$&%04\Uninstall.exe    → ['@$&%04\Uninstall.ini', '0', 'http://...', '8388608']
```

Entries with `['2', '1', ...next_entry...]` are type 2 (stored in the PAK/disc data).

### Language Strings

After the main fields, there are 25+ language blocks with installer UI translations:
```
"English" \x00 "1033" \x00\x00\x00 "French (French)" \x00 "1036" \x00\x00\x00 ...
```
Each language is followed by translated strings for all installer dialog texts.

## Encrypted Payload

The bulk data after the RAR archive is **encrypted** — not ZLIB, not simple XOR.

### Detection
- Entropy ~7.5–8.0/8.0 (near-random)
- No repeating byte patterns at periods 1–32
- No ZLIB or other compression signatures in the bulk
- No file headers visible

### Mechanism
Smart Install Maker v5.04 encrypts the payload using a key derived from the setup password. The password validation code lives in the Delphi PE stub. Without the password:

1. Static extraction is impossible
2. Wine can show the password dialog (run with Xvfb)
3. The PE could be patched to bypass the check
4. Brute-force is possible if the password is weak

## Extraction via Wine

```bash
export WINEPREFIX=~/.wine_extract
export WINEARCH=win32
wineboot -u 2>/dev/null
Xvfb :99 -screen 0 1024x768x16 -ac &
export DISPLAY=:99

# Try silent / help switches
wine installer.exe /HELP
wine installer.exe /VERYSILENT /SUPPRESSMSGBOXES

# Or run interactively (will show GUI)
wine installer.exe
```

## Extraction Workflow Summary

1. Run `file` and `7z l` to identify format
2. Search for "Smart Install Maker" string in binary
3. Parse overlay at that offset (null-separated fields)
4. Extract file manifest from `@$&%04\` entries
5. Check for embedded RAR/ZIP archives via `7z`
6. Check entropy of remaining tail data
7. If encrypted → need password, Wine patching, or brute-force
