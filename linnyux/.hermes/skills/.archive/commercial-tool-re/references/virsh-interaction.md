# virsh-based Windows VM Interaction for RE

Working reference for automating a Windows 11 VM via `virsh` commands for reverse engineering tasks. Covers the full lifecycle: VM setup, NIC management, GUI automation, screenshot analysis, and tool deployment.

## VM Lifecycle

```bash
# Create (one-time)
virt-install --name windows11 --ram 6144 --vcpus 4 \
  --disk path=/var/lib/libvirt/images/windows11.qcow2,size=65 \
  --cdrom /path/to/Win11_25H2.iso \
  --os-variant win11 \
  --graphics spice,port=5901,listen=127.0.0.1 \
  --network network=default,model=e1000e \
  --tpm backend.type=emulator,model=tpm-crb,version=2.0

# Start / Stop
virsh start windows11
virsh shutdown windows11      # graceful
virsh destroy windows11       # force

# Status
virsh domstate windows11
virsh dominfo windows11
```

## NIC Management

### The MAC Duplicate Trap

Every NIC must have a unique MAC. Windows stops responding to ARP with duplicate MACs.

```bash
# List interfaces
virsh domiflist windows11

# Add an e1000e NIC (works without drivers in Windows 11)
virsh attach-interface windows11 network default \
  --model e1000e --mac 52:54:00:77:c3:3b --config

# Add a virtio NIC (high perf, needs driver from virtio-win ISO)
virsh attach-interface windows11 network default \
  --model virtio --mac 52:54:00:76:c3:3b --config

# Remove by PCI address (when multiple NICs share a MAC)
cat > /tmp/detach.xml << 'EOF'
<interface type='network'>
  <mac address='52:54:00:76:c3:3b'/>
  <source network='default'/>
  <model type='e1000e'/>
  <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
</interface>
EOF
virsh detach-device windows11 /tmp/detach.xml --config

# Clean up duplicated NICs in config
# Dump XML, remove all interfaces, re-add cleanly
CPU_MASK=$(case $(nproc) in 2) echo 03;; 4) echo 0f;; 8) echo ff;; *) echo ff;; esac)
```

### NIC Performance Matrix

| Model | Driver | Throughput | Setup |
|-------|--------|-----------|-------|
| `e1000e` | Built-in Windows | ~200 Mbps | Zero effort |
| `virtio` | From virtio-win ISO | ~1 Gbps | Needs driver install |

Strategy: attach BOTH. Use e1000e for immediate network, install virtio driver later, then disable e1000e for speed.

## Storage Management

```bash
# List disks
virsh domblklist windows11

# Attach virtio-win ISO (shutdown required — SATA isn't hotpluggable)
virsh attach-disk windows11 /tmp/virtio-win.iso sdc --type cdrom --config

# Check disk usage
virsh domblkinfo windows11 --disk sdb
```

## GUI Automation (Keyboard)

### Key Reference

| Action | Keys |
|--------|------|
| Login (Ctrl+Alt+Del) | `KEY_LEFTCTRL KEY_LEFTALT KEY_DELETE` |
| Press Space (wake unlock) | `KEY_SPACE` |
| Press Enter | `KEY_ENTER` |
| Tab (next dialog field) | `KEY_TAB` |
| Alt+Y (UAC Yes) | `KEY_LEFTALT KEY_Y` |
| Alt+F4 (close window) | `KEY_LEFTALT KEY_F4` |
| Escape (cancel) | `KEY_ESC` |
| Win+R (Run dialog) | `KEY_LEFTMETA KEY_R` |
| Ctrl+Shift+Enter (Run as admin) | `KEY_LEFTCTRL KEY_LEFTSHIFT KEY_ENTER` |

### Typing Pattern

```bash
# Characters map to KEY_ prefixed names + alphanumeric
# Letters: KEY_A through KEY_Z
# Numbers: KEY_0 through KEY_9
# Special: KEY_DOT, KEY_COLON, KEY_MINUS, KEY_BACKSLASH

# Example: "D:\virtio-win-gt-x64.msi"
virsh send-key windows11 \
  KEY_D KEY_COLON KEY_BACKSLASH KEY_V KEY_I KEY_R KEY_T KEY_I KEY_O \
  KEY_MINUS KEY_W KEY_I KEY_N KEY_MINUS KEY_G KEY_T KEY_MINUS KEY_X \
  KEY_6 KEY_4 KEY_DOT KEY_M KEY_S KEY_I
```

### Launch Pattern for UAC-Sensitive Programs

```bash
# Win+R → type "powershell" → Ctrl+Shift+Enter (admin) → Alt+Y (UAC)
virsh send-key windows11 KEY_LEFTMETA KEY_R
sleep 2
virsh send-key windows11 KEY_P KEY_O KEY_W KEY_E KEY_R KEY_S KEY_H KEY_E KEY_L KEY_L
sleep 1
virsh send-key windows11 KEY_LEFTCTRL KEY_LEFTSHIFT KEY_ENTER
sleep 4
virsh send-key windows11 KEY_LEFTALT KEY_Y
```

## Screenshot Analysis

```bash
# Capture
virsh screenshot windows11 /tmp/ss.png

# Python analysis
python3 -c "
from PIL import Image
img = Image.open('/tmp/ss.png')
w,h = img.size

# Count unique sampled colors
pixels = {}
for x in range(0, w, 30):
    for y in range(0, h, 30):
        p = img.getpixel((x,y))
        pixels[p] = pixels.get(p, 0) + 1

# Classify
grays = sum(c for p,c in pixels.items() if abs(p[0]-p[1])<5 and abs(p[1]-p[2])<5 and p[0]>200)
blues = sum(c for p,c in pixels.items() if p[2] > 150 and abs(p[0]-p[1]) < 30)
dark = sum(c for p,c in pixels.items() if p[0] < 30 and p[1] < 30 and p[2] < 30)
total = sum(pixels.values())

print(f'{len(pixels)} unique sampled colors')
print(f'{grays/total*100:.1f}% grays, {blues/total*100:.1f}% blues, {dark/total*100:.1f}% dark')

if grays > 5 and blues > 5:
    print('STATUS: Desktop visible (likely logged in)')
elif dark/total > 0.9:
    print('STATUS: Black screen (sleeping, booting, or powered off)')
elif len(pixels) < 50:
    print(f'STATUS: Minimal screen (~{len(pixels)} colors)')
else:
    print(f'STATUS: Active UI ({len(pixels)} colors visible)')
"
```

### Detecting Real Changes vs Stale Cache

virsh screenshots may return a cached buffer, especially when SPICE/QXL drivers aren't installed. Compare consecutive snapshots:

```bash
python3 -c "
from PIL import Image
img1 = Image.open('/tmp/ss1.png')
img2 = Image.open('/tmp/ss2.png')
diff = sum(1 for x in range(0,1280,20) for y in range(0,800,20)
           if img1.getpixel((x,y)) != img2.getpixel((x,y)))
print(f'{diff} changed pixel samples')
if diff < 10: print('WARNING: Cache may be stale')
"
```

## Finding VM IP

```bash
# Check DHCP leases
virsh net-dhcp-leases default

# Or inspect the ARP table
arp -n | grep 52:54:00

# Multiple NICs = multiple IPs. The e1000e NIC gets an IP first.
```

## Deploying Tools to VM

Once Windows has network access via e1000e:

1. **Download inside Windows** — Edge/Chrome inside VM downloads the tool directly
2. **Attach ISO with tools** — create an ISO on the Linux host, attach via virsh
3. **Shared folder** — SMB share on host, access from Windows via \\\\192.168.122.1\\
4. **SSH/SCP** — enable OpenSSH Server on Windows via `Add-WindowsCapability`

## Pitfalls Log

- **SPICE/QXL driver must be installed** for accurate screenshots. Without it, only the framebuffer is captured, which may not reflect the actual desktop state.
- **virsh send-key has no feedback mechanism.** You're typing blind. Build verification into the workflow by polling screenshots.
- **Windows 11 Home has no RDP server.** Use Pro/Enterprise or install third-party remote access.
- **Windows Firewall blocks everything inbound** by default (ping, RDP, SMB). Run `netsh advfirewall set allprofiles state off` (admin) to open it up.
- **Duplicate MACs are catastrophic.** Always track each NIC's MAC assignment.
- **SATA CDROM can't be hotplugged.** Must shutdown to attach/change ISOs.
- **TCG emulation is unusably slow.** Always verify `-accel kvm` is in the VM config.
