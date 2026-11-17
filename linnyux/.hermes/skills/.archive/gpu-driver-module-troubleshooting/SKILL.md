---
name: gpu-driver-module-troubleshooting
description: Fix GPU kernel module (NVIDIA/AMD) load failures on Ubuntu — DKMS build errors, missing kernel headers, .ko.zst compression failures, package conflicts, and mixed-version contamination. Use when nvidia-smi fails, modprobe can't find modules, or DKMS post-install scripts error out.
---

# GPU Driver Module Troubleshooting

Fix GPU kernel modules that won't build or load on Ubuntu. Covers NVIDIA primarily (most common) and AMD patterns where applicable.

## Trigger conditions

Use this skill when:
- `nvidia-smi` says "couldn't communicate with NVIDIA driver"
- `sudo modprobe nvidia` says "FATAL: Module nvidia not found"
- `dpkg --configure -a` fails on `linux-modules-nvidia-*` packages
- DKMS build errors in apt post-install scripts
- `/var/crash/*nvidia*.crash` files exist indicating module build failure
- `/lib/modules/$(uname -r)/kernel/nvidia-*/` exists but has `.o` or sig files only, no `.ko.zst`

## Diagnostic pipeline

### 1) Check the module files exist

```bash
# Look for compiled module files
find /lib/modules/$(uname -r) -name 'nvidia.ko*' 2>/dev/null
```

Possible outcomes:
| Result | Meaning |
|--------|---------|
| `nvidia.ko.zst` found | Module exists and is loadable — check modprobe config |
| `nvidia.ko` found (no .zst) | Object files exist but not compressed — compression step failed |
| `nvidia.o` / `.sig` only | Only partial build artifacts — build never completed |
| Nothing found | Package not installed for this kernel |

### 2) Check the package status

```bash
dpkg -l linux-modules-nvidia-*-$(uname -r | sed 's/-generic//')-generic 2>/dev/null | grep ^[ip]

# Check if the package actually has files
dpkg -L linux-modules-nvidia-*-$(uname -r | sed 's/-generic//')-generic 2>/dev/null | head -5
```

Status codes:
- `ii` — installed (but may have zero files if post-install failed and was forced)
- `pc` — purged, config files remain
- `rc` — removed, config files remain
- `iU` — unpacked but not yet configured (broken)

### 3) Check kernel headers

```bash
ls /usr/src/linux-headers-$(uname -r)/scripts/module.lds 2>/dev/null
```

If the linker script is missing, the NVIDIA post-install build will fail with:
```
/usr/bin/ld.bfd: cannot open linker script file /usr/src/linux-headers-<KVER>/scripts/module.lds: No such file or directory
```

Check if the headers package is installed:
```bash
dpkg -l linux-headers-$(uname -r) 2>/dev/null | grep ^[ip]
```

### 4) Check for mixed driver versions

```bash
dpkg -l | grep 'nvidia.*modules' | grep -oP 'nvidia-\K\d+'
```

Multiple versions (e.g. both 535 and 580) cause symbol conflicts. Only one should be present.

Also check for **same-directory duplicate module files of different versions** — a partial update can leave BOTH a new uncompressed `*.ko` and a stale older `*.ko.zst` for the same module in one `/lib/modules/<ver>/kernel/nvidia-580/` dir. depmod then resolves `nvidia.ko` to the new version but `nvidia-modeset`/`drm`/`uvm` to the stale `.zst`, and the kernel logs `nvidia-modeset: Version mismatch: nvidia.ko(A.B) nvidia-modeset.ko(C.D)` → modeset fails to init (latent black-screen/wedge risk on Optimus). Detect and fix:

```bash
cd /lib/modules/$(uname -r)/kernel/nvidia-580/
# find which PHYSICAL file modprobe currently resolves each module to
modinfo -F filename nvidia-modeset
# identify the version of EACH on-disk file (.ko AND .ko.zst)
for f in *.ko *.ko.zst; do echo "$f -> $(modinfo -F version "$f" 2>/dev/null)"; done
# the on-disk files that do NOT match the installed package version (nvidia-kernel-common-*) are stale
sudo mkdir -p /root/nvidia-stale-backup && sudo mv -v *.ko.zst /root/nvidia-stale-backup/   # if .zst is the stale set
sudo depmod -a
# verify ALL modules now resolve to the SAME (installed-package) version
for m in nvidia nvidia-modeset nvidia-drm nvidia-uvm; do echo "$m -> $(modinfo -F version $m)"; done
```

Back up the stale files rather than hard-deleting (reversible). The fix fully applies next reboot; an Intel-driven (Optimus) live session is unaffected.

## Fix workflow

### Missing kernel headers

```bash
sudo apt install -y linux-headers-$(uname -r)
```

Then reinstall the NVIDIA module package.

### Broken module package (purge + reinstall)

```bash
# Identify the exact package name
PKG=$(dpkg -l | grep "linux-modules-nvidia-.*-$(uname -r | sed 's/-generic//')-generic" | awk '{print $2}')

sudo dpkg --purge "$PKG"
sudo apt install -y "$PKG"
```

### Manual .ko.zst compression (when headers weren't the issue)

When `.ko` files exist in `/lib/modules/$(uname -r)/kernel/nvidia-*/` but are uncompressed:

```bash
sudo sh -c '
for d in /lib/modules/$(uname -r)/kernel/nvidia-*/; do
  [ -d "$d" ] || continue
  (cd "$d" && for f in *.ko; do
    [ -f "$f" ] && zstd --rm -f "$f" -o "${f}.zst"
  done)
done
depmod -a'
```

### Remove conflicting older driver versions

```bash
# Find all non-current NVIDIA module packages
dpkg -l | grep 'linux-modules-nvidia-' | grep -v $(uname -r | sed 's/-generic//') | awk '{print $2}' | xargs -r sudo apt purge -y
```

### Verify the fix

```bash
sudo modprobe nvidia
sudo modprobe nvidia-drm
nvidia-smi
```

Expected output shows the GPU model, driver version, and CUDA version:
```
GPU 0: NVIDIA GeForce ... | Driver: 580.xxx.xx | CUDA: xx.x | 4MiB / 4096MiB
```

## Pitfalls

- **`nvidia-smi` failure on Optimus laptops does NOT mean broken graphics.** The Intel GPU drives the display; the NVIDIA driver only enables CUDA/compute. A failed NVIDIA module and a black screen are separate problems.
- **The package may say "ii" (installed) but have zero files** — `dpkg -L` returns "Package does not contain any files (!)". The post-install script failed but dpkg was forced through. Purge and reinstall.
- **`nvidia.ko` is ~122MB** for the 580 driver. ZSTD compression takes ~60 seconds. Don't timeout the command.
- **Always run `depmod -a` after manual compression** — without it, `modprobe` won't discover the new `.ko.zst` files.
- **Mixed 535 + 580 installations** cause "undefined symbol" errors at module load time. Purge the old version before installing the new one.
- **Kernel updates break NVIDIA modules** — every kernel upgrade requires matching `linux-modules-nvidia-*` packages. Check after apt upgrades.
- **`nvidiafb` is blacklisted by default** in `/etc/modprobe.d/blacklist-framebuffer.conf` — that's normal and irrelevant. The NVIDIA display driver module is `nvidia-drm`, not `nvidiafb`.
