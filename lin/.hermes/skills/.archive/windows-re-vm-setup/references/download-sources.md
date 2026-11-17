# Windows ISO Download Sources

Microsoft's official download page requires navigating complex JavaScript-driven forms and often redirects to the Media Creation Tool instead of providing a direct ISO link. These are reliable alternatives.

## massgrave.dev (first try, but Cloudflare-gated)

MAS (Microsoft Activation Scripts) hosts download links for genuine Windows ISOs:

```
https://massgrave.dev/windows_11_links.html
```

- Links go through zerofs.link redirector (e.g. `https://zerofs.link/f/7ibXMho/`)
- Updated monthly on Patch Tuesday
- Consumer, Business, IoT Enterprise, ARM64 variants all available
- Multi-language table layout

### Cloudflare Turnstile blocks direct download

The zerofs.link pages have Cloudflare Turnstile ("Verify you are human") that blocks curl/wget/aria2. Browser automation also fails — the captcha needs a real human solve. Try WARP VPN as a workaround, or skip straight to uupdump.net.

## uupdump.net (reliable — no captcha, works from Linux)

When massgrave/zerofs is blocked by Cloudflare, use UUP dump. Downloads raw UUP files from Microsoft's own CDNs and converts to a bootable ISO. No captcha, works entirely from CLI.

### Steps

1. Navigate to https://uupdump.net/
2. Click **"Latest Public Release build"** → select **x64**
3. Select language → **English (United States)**
4. Select editions → at least **Windows Home** + **Windows Pro** (default)
5. On the summary page, select **"Download UUP set"** (NOT "Download and convert to ISO" — that requires Windows)
6. Click **"Create download package"** → downloads a ZIP with aria2 scripts

### Run on the VM host

```bash
unzip 26200.8968_amd64_en-us_multi_*.zip -d /tmp/windows-iso
cd /tmp/windows-iso
chmod +x uup_download_linux.sh
./uup_download_linux.sh
```

Downloads ~6-11 GiB of cabinet files into a `UUPs/` subdirectory.

### Convert to ISO on Linux

```bash
git clone https://git.uupdump.net/uup-dump/converter.git /tmp/uup-converter
cd /tmp/uup-converter
chmod +x uup-converter-linux.sh
./uup-converter-linux.sh /tmp/windows-iso/UUPs
```

Depends on cabextract, cdrtools/genisoimage.

### API details

The download.php URL format:
```
https://uupdump.net/download.php?id=<UUID>&pack=<lang>&edition=<edition1>;<edition2>
```

Edition values: `CORE`, `COREN`, `PROFESSIONAL`, `PROFESSIONALN`
Key parameter: `aria2=2` triggers direct script output instead of a ZIP.

### Total download size

Windows 11 25H2 UUP set: approximately **10.73 GiB**.

## Microsoft Official (least reliable)

```
https://go.microsoft.com/fwlink/p/?LinkID=2195404&clcid=0x409&culture=en-us&country=US
```

Returns an empty page (bot detection) or redirects to the Media Creation Tool. Avoid.

## Fresh Install Checklist (skip BitLocker)

To avoid BitLocker complications on an RE VM, when starting the install press **Shift+F10** at the first setup screen and run:

```cmd
reg add HKLM\SYSTEM\Setup\LabConfig /v BypassTPMCheck /t REG_DWORD /d 1 /f
reg add HKLM\SYSTEM\Setup\LabConfig /v BypassSecureBootCheck /t REG_DWORD /d 1 /f
reg add HKLM\SYSTEM\Setup\LabConfig /v BypassRAMCheck /t REG_DWORD /d 1 /f
reg add HKLM\SYSTEM\Setup\LabConfig /v BypassStorageCheck /t REG_DWORD /d 1 /f

:: Disable BitLocker / device encryption
reg add HKLM\SYSTEM\CurrentControlSet\Control\BitLocker /v PreventDeviceEncryption /t REG_DWORD /d 1 /f
```

Also bypass the Microsoft Account requirement:

```cmd
reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\OOBE /v BypassNRO /t REG_DWORD /d 1 /f
```

Then `shutdown /r /t 0`. The install continues with local account only and no BitLocker.

## Utilman Swap Before First Boot

For RE VMs, the ideal workflow is:

1. Install Windows with BitLocker disabled (see above)
2. Before the first boot into Windows, mount the qcow2 via qemu-nbd
3. Do the utilman swap offline:
   ```bash
   modprobe nbd max_part=8
   qemu-nbd --connect=/dev/nbd0 /var/lib/libvirt/images/windows11.qcow2
   mount /dev/nbd0pX /mnt/windows  # the Windows partition
   cd /mnt/windows/Windows/System32
   mv utilman.exe utilman.exe.bak
   copy cmd.exe utilman.exe
   umount /mnt/windows
   qemu-nbd --disconnect /dev/nbd0
   ```
4. Boot the VM normally. At the PIN/login screen, click the Ease of Access icon → SYSTEM cmd prompt.
