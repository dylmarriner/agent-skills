# kubuntux Windows VM — Environment Reference

Specific details for the Windows RE VM setup on kubuntux.

## Host Specs
| Field | Value |
|-------|-------|
| Hostname | kubuntux |
| Tailscale IP | 100.93.75.87 |
| Hardware | HP Pavilion, i7-6700, 16GB RAM |
| Libvirt storage | /var/lib/libvirt/images/ |
| Extra storage | /mnt/storage (415GB free) |

## Storage Layout
| Path | Purpose |
|------|---------|
| `/var/lib/libvirt/images/` | Active VM disks + ISOs |
| `/mnt/storage/VMs/iso/` | Archive of downloaded ISOs |
| `/mnt/storage/VMs/images/` | Archive of old VM disk images |
| `/home/kubuntux/Downloads/RE/` | RE tool installers + extracted output |
| SMB `//192.168.122.1/RE` | Samba share = Downloads/RE |

## Existing ISOs
- `/mnt/storage/VMs/iso/Win11_25H2_EnglishInternational_x64_v2.iso` — 8.0GB, official Microsoft ISO (en-gb). UEFI-bootable. **The working ISO for VM installs.**
- `/mnt/storage/VMs/iso/virtio-win.iso` — 789MB, virtio drivers.

## Existing VM Images
- `/mnt/storage/VMs/images/Windows11.qcow2` — 64GB virtual, 11MB actual. Old install attempt, no completed Windows.

## Session Artifacts (2026-07-27)
| File | Purpose |
|------|---------|
| `/var/lib/libvirt/images/Win11_official.iso` | Copy of official ISO (copied from /mnt/storage) |
| `/var/lib/libvirt/images/win11.qcow2` | Current VM disk (fresh, empty) |
| `/tmp/win11_*.xml` | Multiple VM config iterations (on kubuntux) |
| `/var/lib/libvirt/images/Win11_unattended.iso` | UUP-converted ISO with modified boot.wim (BIOS-only, doesn't boot in KVM) |

## VM Config Pitfalls (discovered 2026-07-27)

1. **q35 + OVMF + `bus=sata` maps to IDE, not AHCI.** Despite the parameter name, libvirt maps SATA-attached disks to `ide-hd`/`ide-cd` QEMU devices on q35. OVMF can't enumerate these. All VM configs using `bus=sata` on q35 fail with "No bootable option or device was found."

2. **virt-install `--boot uefi` produces the same mapping.** virt-install generates the same `bus=sata` → IDE mapping. OVMF can't boot.

3. **i440fx + OVMF also fails.** The IDE controller on i440fx (PIIX3) has the same OVMF enumeration issue.

4. **SeaBIOS (i440fx, no OVMF) boots everything.** SeaBIOS has working IDE drivers. The official ISO boots to the Windows setup screen (disk grows to 328KB). But Windows 11 setup detects the BIOS/CSM boot and will refuse to install.

5. **`--nvram` destroys swtpm state.** `virsh undefine --nvram` deletes BOTH the NVRAM file AND `/var/lib/libvirt/swtpm/<uuid>/tpm2/tpm2-00.permall`. Permanent lockout for BitLocker VMs.

6. **UEFI boot on q35 is broken for Linux-built ISOs.** UUP converter ISOs lack proper El Torito EFI entries. Even xorriso with `-isohybrid-gpt-basdat` doesn't reliably fix this.

## Quick VM Reset
```bash
virsh destroy windows11 2>/dev/null
virsh undefine windows11 --nvram 2>/dev/null
rm -f /var/lib/libvirt/images/win11.qcow2
qemu-img create -f qcow2 /var/lib/libvirt/images/win11.qcow2 60G
# Copy official ISO from archive if needed
cp /mnt/storage/VMs/iso/Win11_25H2_EnglishInternational_x64_v2.iso /var/lib/libvirt/images/Win11_official.iso

# Define + start with virt-install (known to produce IDE bus -> may not boot)
virt-install --name windows11 --ram 4096 --vcpus 2 --cpu host-passthrough \
  --disk /var/lib/libvirt/images/win11.qcow2,bus=sata \
  --cdrom /var/lib/libvirt/images/Win11_official.iso \
  --os-variant win11 \
  --boot uefi,cdrom,hd \
  --graphics spice,listen=127.0.0.1 \
  --tpm backend.type=emulator,model=tpm-crb,version=2.0 \
  --noautoconsole
```
