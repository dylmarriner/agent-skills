# VM Resource Sizing Guidelines

## Rule of Thumb

**Never allocate more than 40% of host RAM to a single VM.** The host OS, desktop environment, browser, and other services need breathing room. Swap thrashing from an overprovisioned VM makes the entire machine unusable.

## kubuntux (i7-6700, 4C/8T, 16GB RAM)

| VM Purpose | vCPUs | RAM | Notes |
|-----------|-------|-----|-------|
| RE tools (idle desktop) | 2 | 4GB | Minimum viable for Windows 11 |
| RE tools (active use) | 2-3 | 4-6GB | Good balance, leaves 8-10GB for host |
| Heavy RE suite | 4 | 6-8GB | Push it but monitor swap |
| ✅ Current windows11 | 2 | 4GB | Resized 2026-07-19 — smooth, no swap pressure |

## Host-Side Monitoring

```bash
# Check if swapping is happening
free -h | grep Swap

# Find the VM hog
ps aux --sort=-%mem | head -5

# Check specific VM allocation
virsh dominfo <vm> | grep -i mem
```

## Shrinking a VM

Two methods — `virsh edit` for precision, or direct commands for speed:

### Method A: direct virsh commands (faster, no editor)

```bash
virsh destroy <vm>  # force-stop (or virsh shutdown for graceful)
# Wait for VM to stop
virsh setvcpus <vm> <n> --maximum --config
virsh setvcpus <vm> <n> --config
virsh setmaxmem <vm> <kibibytes> --config
virsh setmem <vm> <kibibytes> --config
virsh start <vm>
```

Example (10GB → 4GB, 5 vCPUs → 2):
```bash
virsh destroy windows11
virsh setvcpus windows11 2 --maximum --config
virsh setvcpus windows11 2 --config
virsh setmaxmem windows11 4194304 --config   # 4GB = 4194304 KiB
virsh setmem windows11 4194304 --config
virsh start windows11
```

### Method B: virsh edit (precise, opens editor)

```bash
virsh shutdown <vm>
virsh edit <vm>   # edit <memory>, <currentMemory>, <vcpu>
virsh start <vm>
```

Windows will see the reduced RAM/vCPUs on next boot — no guest-side changes needed.
