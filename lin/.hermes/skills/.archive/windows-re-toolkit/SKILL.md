---
name: windows-re-toolkit
description: Install and use reverse-engineering tools on Linux for Windows binary (PE/.NET) analysis. Covers Ghidra, ILSpy, Detect It Easy, pev, Python RE libs, and techniques for acquiring Windows binaries from ad-wall file hosts.
related_skills:
  - install-tool-from-github-url
  - install-agent-tools
---

# Windows Reverse-Engineering Toolkit

Set up a complete Windows binary analysis environment on Linux. Covers tool installation, ad-wall download navigation, first-pass reconnaissance, and deep decompilation workflow.

## Trigger Conditions

- User says "install ghidra", "install ilspy", "install die", "install detect it easy", "install re tools"
- User asks to "tear apart", "strip apart", "reverse engineer", "decompile", "analyze" a Windows `.exe` / `.dll`
- User sends a download link to a Windows binary from a sketchy file host (filexspace, earnarab, mediafire, etc.)
- User says "what tool can I use to RE a Windows app"

## Tool Installation

### Ghidra (native PE decompiler — C pseudocode)

```bash
# Check JDK first
java -version  # need JDK 21+

# Find latest release URL
curl -s "https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest" \
  | grep -E '"tag_name"|browser_download_url.*zip"'

# Download (~570MB)
curl -L -o ~/Downloads/ghidra.zip "https://github.com/.../ghidra_<VERSION>_PUBLIC_<DATE>.zip"

# Extract to /opt
sudo unzip ~/Downloads/ghidra.zip -d /opt/
sudo mv /opt/ghidra_<VERSION>_PUBLIC /opt/ghidra
sudo ln -sf /opt/ghidra/ghidraRun /usr/local/bin/ghidra
```

**Usage:** `ghidra` (GUI, needs X11/Wayland display)

### ILSpy / AvaloniaILSpy (.NET decompiler)

```bash
# Need .NET SDK first
sudo apt-get install -y dotnet-sdk-8.0

# Find latest release
curl -s "https://api.github.com/repos/icsharpcode/AvaloniaILSpy/releases/latest" \
  | grep -E '"tag_name"|browser_download_url.*Linux.x64'

# Download (~50MB) and extract
curl -L -o ~/Downloads/ilspy.zip "https://github.com/.../Linux.x64.Release.zip"
sudo mkdir -p /opt/ilspy
sudo unzip ~/Downloads/ilspy.zip -d /opt/ilspy/
# Binary is at /opt/ilspy/artifacts/linux-x64/ILSpy
sudo ln -sf /opt/ilspy/artifacts/linux-x64/ILSpy /usr/local/bin/ilspy
```

**Usage:** `ilspy` (GUI, needs X11/Wayland display)

### Detect It Easy (DIE — packer/compiler identification)

```bash
# Find latest Linux release URL
curl -s "https://api.github.com/repos/horsicq/Detect-It-Easy/releases" \
  | grep browser_download_url.*Ubuntu.*amd64 | head -1

# Download and install (~9MB .deb)
curl -L -o ~/Downloads/die.deb "https://github.com/.../die_<VER>_Ubuntu_24.04_amd64.deb"
sudo dpkg -i ~/Downloads/die.deb
sudo apt-get install -y -f  # fix deps (libqt5script*)
```

**Alternative (manual extract if .deb fails):**
```bash
mkdir -p /tmp/die_extract && cd /tmp/die_extract
dpkg-deb -x ~/Downloads/die.deb .
sudo cp usr/bin/die /usr/local/bin/
sudo cp usr/bin/diec /usr/local/bin/  # console version
sudo cp -r usr/lib/die /usr/lib/
sudo apt-get install -y libqt5script5 libqt5scripttools5
```

**Usage:** `die <file>` (GUI), `diec <file>` (console)

### pev tools (CLI PE header analysis)

```bash
sudo apt-get install -y pev
# Tools: readpe, pestr, pescan, peinfo, peupdate, etc.
```

### Python RE environment

```bash
python3 -m venv ~/venvs/re-tools
~/venvs/re-tools/bin/pip install pefile capstone lief
# Use: source ~/venvs/re-tools/bin/activate
```

### innoextract (Inno Setup installer extraction)

Many mobile-repair tools ship as Inno Setup installers. Extract them statically.

```bash
sudo apt-get install -y innoextract
innoextract -d output_dir installer.exe     # Extract without running
```

### iconv (UTF-16 config file reader)

Many Windows tools ship UTF-16-encoded INI/language files. These are plaintext once converted and often reveal the entire capability surface when the binaries are packed.

```bash
iconv -f UTF-16 -t UTF-8 app/Settings.ini   # Read multi-language configs
```

## Acquiring Binaries from Ad-Wall File Hosts

Many GSM/mobile-repair tools (TFT Unlock, SamFw, etc.) are distributed through file hosts with aggressive ad walls. Download links look like normal clickable buttons but route through redirect farms.

### Typical ad-wall hosts
- `filexspace.com` — password-protected zips, ad-wall countdown
- `earnarab.com` — affiliate redirect chain
- `mediafire.com` — legitimate host but links often behind redirect

### Workflow for acquisition

1. **Identify actual download URL from the page source:**
   ```javascript
   // Extract via browser DevTools console:
   document.querySelectorAll('a[href]').forEach(a => {
     let h = a.getAttribute('href');
     console.log(a.textContent.trim().substring(0,40), '→', h);
   });
   ```

2. **Navigate through ad-wall redirects in browser:**
   - Click the download button
   - Note the `window.open()` target or the redirect chain
   - The file host page will show filename, size, and a "DOWNLOAD FILE" button
   - Some require a password (commonly `123`)

3. **Download via curl with referrer (if the host allows direct links):**
   ```bash
   curl -L -o outfile.exe "https://filexspace.com/getfile/TOKEN" \
     -H "Referer: https://tfttool.com/"
   ```
   Most ad-wall hosts block direct curl — use browser automation to click through to the actual download.

4. **If the browser gets stuck on an empty page (redirect chain to affiliate networks):**
   The file host redirected to an ad network affiliate link (e.g. `playstretch.host`, `structurebee.icu`).
   Try a different download mirror, or use the alternative "GOOGLE DRIVE LINK" if available.

## First-Pass Reconnaissance Workflow

When the target binary arrives:

```bash
# 0. If the target is an installer, extract it first
file target.exe                     # Check if Inno Setup / NSIS / InstallShield
innoextract -d extracted target.exe # Extract Inno Setup installers statically
find extracted -type f -name '*.exe' -o -name '*.dll' | head -20   # Find the real binaries

# 1. Identify the file type of all PE files
file app/*.exe app/*.dll

# 2. Quick PE header analysis — watch for VMProtect indicators
readpe target.exe                   # DOS header, NT headers, sections
pescan target.exe                   # Detect packer/protector
# VMProtect signature: section names .vmp0/.vmp1, entropy ~7.89, zero-length .text
# Check section count (12+ is suspicious), TLS directory presence

# 3. Extract DLL exports to understand the API surface (before packing obscures it)
# For DLLs: this reveals the full protocol/function surface even when packed
readpe -E libexample.dll            # List exported functions
# NOTE: Some VMProtect-packaged DLLs still export their originals

# 4. Read UTF-16 config/language files for capability clues
# When binaries are VMProtected and strings are garbage, this is your best source:
iconv -f UTF-16 -t UTF-8 app/Settings.ini 2>/dev/null | grep -E '(URL|http|debug|password|key|license|s/n|serial)'
# Language files often contain every UI string, error message, debug log, and feature name

# 5. Check driver INF files for USB hardware IDs
cat app/Driver/*/*.inf 2>/dev/null | grep -i 'VID_' | sort -u
# Gives you the USB VID/PID — useful for hardware identification
# Also check: grep -i 'DeviceName\|Manufacturer' *.inf

# 6. DIE for compiler/packer identification
diec target.exe                     # Console mode (also detects VMProtect directly)

# 7. Extract strings — expect garbage if VMProtect is present
strings target.exe | sort | uniq -c | sort -rn | head -50
pestr target.exe                    # PE-specific string extraction
# If entropy > 7.5 and .vmp sections exist, strings will be ~98% garbage — don't waste time

# 8. Deep analysis — Ghidra (will see VM bytecode without unpacking first)
ghidra                              # Open GUI → create project → import .exe → auto-analyze

# 9. If .NET detected — ILSpy
ilspy                               # Open GUI → File → Open → select .exe/.dll
```

## What to Look For (typical unlock tools)

- **License/activation check** — HTTP requests to licensing servers, trial expiry, HWID binding
- **USB communication protocols** — libusb/winusb calls, Samsung download mode sequence, ADB commands
- **FRP bypass methods** — strings containing "frp", "bypass", "remove", "reset"
- **API endpoints** — hardcoded URLs for activation servers or credential validation
- **Embedded credentials** — API keys, tokens, passwords in plaintext or obfuscated
- **Driver installation routines** — embedded .sys or .inf files
- **USB VID/PID** — from INF driver files: identifies the custom hardware dongle
- **Dual-brand identity** — the installer filename and internal product name may differ (e.g. "Octoplus 1.9.5.6" installer containing "Medusa Box 2.6.1.7")
- **Feature surface from config files** — when binaries are packed, the language/INI file reveals everything: modes, operations, error codes, debug logging, emergency key combos, supported chipset families

## References

See `references/tft-unlock-specifics.md` for detailed info about the TFT Unlock tool (versions, download sources, RE targets).
See `references/winlice-unpacking.md` for Winlice packer analysis details, including LZSS stub location, decompression approach, and the Windows VM requirement for runtime OEP dumping.

## Pitfalls

- **Ghidra download is ~570MB** — takes 30-60s on good connection. Don't assume it failed silently.
- **ILSpy .NET tool install via NuGet fails** (`nuget.exe tool install ilspy` doesn't exist). Use the AvaloniaILSpy self-contained binary instead.
- **DIE .deb may fail to install** due to missing Qt5 deps. Fix with `apt-get install -y -f` or extract the .deb manually.
- **Ad-wall file hosts block direct curl** — you need browser automation with proper referrer headers or user-agent spoofing to get past the landing page.
- **Do not try to run Windows binaries on Linux** — they won't execute. The tools decompile statically.
- **VMProtect-packed binaries produce ~98% garbage strings** — don't waste time grepping for passwords/URLs in `strings` output. Read UTF-16 config INI files instead; those are not protected and contain the full feature surface.
- **VMProtect detection**: look for `.vmp0`/`.vmp1` section names, entropy > 7.8, zero-length `.text` section, section count >= 11. `pescan` will flag "probably packed" and show suspicious section names.
- **Winlice packer**: look for `.winlice` and `.boot` sections. Entry point inside `.boot`. LZSS decompression stub at boot offset ~0x58 using `adc`/`rcl` bit ops. Single import per DLL. Static LZSS produces a ~6.4MB blob with MZ header but scrambled — needs Windows VM with debugger (x64dbg + ScyllaHide) for runtime OEP dump.
- **Read UTF-16 configs when packed** — Language/INI files shipped with installers are never packed. For Octoplus/Chimera/Medusa, they reveal the full feature surface, device list, and operation names.
- **VMProtect still exports DLL functions** — `readpe -E lib.dll` on a VMProtected DLL still shows the original export names (the exports table is not obfuscated). This is your best source for the API surface.
- **Some installers misidentify themselves** — the filename may say one product/version while the Inno Setup metadata says another. Check the extraction output header line (e.g. `Extracting "Medusa Box Software 2.6.1.7"` vs filename `install_Octoplus_JTAG_1.9.5.6.exe`).
