# MediaTek SLA Key Extraction from Preloader

## Background

MediaTek Dimensity BROM requires SLA (Secure Boot Loader Attestation) authentication. The RSA key pair (n, e, d) is embedded in the device's preloader binary. Extracting this key and adding it to mtkclient's `sla_keys.py` allows bypassing SLA without paid tools.

## Key Format in sla_keys.py

```python
class SlaKey:
    vendor = None     # e.g., "Xiaomi"
    da_codes = []     # DA codes this key matches (empty = try for all)
    name = None       # description string
    d = None          # RSA private exponent (int or hex string)
    n = None          # RSA modulus (int or hex string)
    e = None          # RSA public exponent (usually "010001" = 65537)

# Example:
SlaKey(vendor="Xiaomi", da_codes=[],
       name="MT6833 Dimensity 6080",
       d=<private_exponent>,
       n=<modulus>,
       e="010001")
```

## Key Locations

The key is in `Library/Auth/sla_keys.py` inside the mtkclient install:
- BROM keys: `brom_sla_keys` list (line 125)
- DA keys: `da_sla_keys` list (line 39)

## Finding the Key in Preloader Binary

### Method 1: Search for ASN.1 DER structure

RSA 2048-bit keys in DER format start with `30 82` followed by the key structure:

```
xxd preloader.bin | grep "3082"
```

### Method 2: String search for key references

```
strings preloader.bin | grep -i "sla\|rsa\|oemkey\|img_auth"
```

### Method 3: Firmware extraction

1. Download stock fastboot ROM for the device from xiaomistockrom.com
2. Extract the zip/tgz — preloader is typically `images/preloader_<codename>.bin` or `preloader.img`
3. Search for RSA modulus patterns (256 bytes = 512 hex chars)

## Porting from auth_sv5.auth (Official Xiaomi Firmware)

Xiaomi fastboot ROM archives include `auth_sv5.auth` — a proprietary MediaTek MMM container that holds auth keys. It uses `MMM\x01` containers. The MTK container holds RSA key data. Extract with mtkclient flags:
```bash
mtk --auth auth_sv5.auth --loader MTK_AllInOne_DA.bin printgpt
```
The `--auth` flag parses the MMM container internally rather than relying on baked-in keys.

RSA key regions found at offsets 0x270, 0x47c, 0x688 within the MTK container. These are raw 256-byte chunks but in an auth_sv5-specific format — direct integer extraction to sla_keys.py format was not completed.

### Method 4: Port from DA keys

Xiaomi often reuses the same RSA key pair for DA and BROM SLA. If a DA key exists in `da_sla_keys` for the chipset, port it to `brom_sla_keys` by adding a `SlaKey` entry with the same `n`, `d`, `e` values. The Xiaomi DA AuthKey (index 7 in da_sla_keys) is a candidate for Dimensity 6080.

## How BROM SLA Challenge Works

From `mtk_preloader.py` `handle_sla()`:

1. For each key in `brom_sla_keys`:
   a. Send SLA command
   b. Read challenge data from device
   c. Sign: `generate_brom_sla_challenge(data=challenge, d=key.n, e=key.d)`
   d. Send response back
   e. If accepted → proceed; if rejected → try next key

The signature is byte-swapped PKCS#1 v1.5: `customized_sign(n, d, msg)` computes `msg^d mod n`.

## Existing MT6833 Files

- `payloads/mt6833_payload.bin` — generic patcher, NOT device-specific key
- `Loader/Preloader/preloader_oppo6833.bin` — Oppo variant, different key
- `Loader/Preloader/preloader_k6833v1_64.bin` — K6833 variant
- `Loader/Preloader/preloader_gfive89_6833b.bin` — GFive variant

None of these contain the Redmi Note 13 5G key. Download the actual gold/iron firmware preloader.

## Pitfalls

- The DA SLA uses `generate_da_sla_signature` (OAEP+SHA256) while BROM uses `generate_brom_sla_challenge` (PKCS#1 v1.5) — same RSA key works for both, but the signing functions are different
- Parameter naming in mtkclient is confusing: `generate_brom_sla_challenge(data, d, e)` uses `d` as modulus and `e` as exponent
- The Xiaomi DA key has `da_codes=[]` (empty) meaning it won't auto-match any specific device — it must be tried generically

## Alternative: SP Flash Tool under Wine (Mi Flash/SP_Download_tool)

When mtkclient's baked-in keys don't match, the official Xiaomi/MediaTek SP Flash Tool can handle SLA via `auth_sv5.auth` and `MTK_AllInOne_DA.bin` from the stock firmware. It has a native `Authentication.dll` with proper SLA support.

**What's in the MiFlash20220507 package:**

| Component | Path | Purpose |
|-----------|------|---------|
| SP_download_tool.exe | `SP_Download_tool/` | CLI flashing tool (runs under Wine) |
| Authentication.dll | `SP_Download_tool/` | SLA auth — exports `sec_init_key`, `sec_auth_challenge`, `sec_hash`, `sec_verify` |
| auth_sv5.auth | `da/` or `mi/` | RSA key container (MMM format) |
| MTK_AllInOne_DA.bin | `da/` | Download Agent binary |
| FlashToolLib.dll | root | Native flashing protocol (Brom_SendSCERT, AUTH_Load, etc.) |

**How to use:**

```bash
cd SP_Download_tool/
wine SP_download_tool.exe --help  # Verify it runs

# Full flash command (needs scatter file from firmware):
wine SP_download_tool.exe -scatter <path>/MT6833_Android_scatter.txt \
    -auth ../da/auth_sv5.auth -da ../da/MTK_AllInOne_DA.bin
```

The tool requires BROM mode (0e8d:2000). Phone must be in BROM before running. SP Flash Tool automatically handles: SLA challenge/response via Authentication.dll → DA upload → flash/format operations.

**Authentication.dll internals:**

- `sec_init_key(auth_data, size, &ctx)` — parses auth_sv5.auth, initializes RSA context
- `sec_auth_challenge(challenge, challenge_len, response, &resp_len)` — signs BROM challenge
- `sec_verify(auth_data, challenge, signature)` — verifies a signature

To extract the key programmatically without Wine: write a minimal C program linking Authentication.dll, call `sec_init_key` with the auth file, dump the internal key context. Requires mingw-w64 cross-compiler.

**Partial firmware download trick:**

Full fastboot ROM is 5-7GB but the auth/DA files are under 800KB total. Download the firmware archive and interrupt it after 50-100MB. Extract with `tar xzf` — it will error on EOF but the auth_sv5.auth, MTK_AllInOne_DA.bin, and flash scripts are at the start of the archive and extract successfully.

## Pitfalls

- The DA SLA uses `generate_da_sla_signature` (OAEP+SHA256) while BROM uses `generate_brom_sla_challenge` (PKCS#1 v1.5) — same RSA key works for both, but the signing functions are different
- Parameter naming in mtkclient is confusing: `generate_brom_sla_challenge(data, d, e)` uses `d` as modulus and `e` as exponent
- The Xiaomi DA key has `da_codes=[]` (empty) meaning it won't auto-match any specific device — it must be tried generically
