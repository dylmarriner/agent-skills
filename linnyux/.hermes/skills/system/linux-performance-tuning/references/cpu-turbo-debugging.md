# CPU Turbo Debugging via MSR Registers

Diagnose why a CPU isn't reaching its advertised max turbo frequency. This is the MSR-level deep dive — use after confirming scaling_governor=performance, scaling_max_freq=4000000, and the CPU still won't boost.

## Quick Check — Scaling Layer (no sudo needed)

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver
```

If governor=performance, max=4000000, driver=intel_pstate, but cur is stuck at ~3700000 under single-core load — move to MSR analysis.

## MSR Tools

```bash
# Install
sudo apt-get install msr-tools
sudo modprobe msr

# Read a register
sudo rdmsr -p 0 0x1ad           # hex output
sudo rdmsr -f 15:0 -p 0 0x1ad   # extract specific bitfield
```

## Step 1 — Turbo Ratio Limits (0x1ad)

This register tells you what the CPU *should* be capable of:

```bash
sudo rdmsr 0x1ad
```

Expected output e.g. `25262728` — packed as 4 bytes:
- `0x28` (40d) = 1-core ratio → 4.0 GHz
- `0x27` (39d) = 2-core ratio → 3.9 GHz
- `0x26` (38d) = 3-core ratio → 3.8 GHz
- `0x25` (37d) = 4-core ratio → 3.7 GHz

If these look correct, the CPU is capable. The question becomes: what's stopping it?

## Step 2 — HWP Capabilities and Request (0x771, 0x774)

Only relevant if HWP (Hardware P-State) is enabled:

```bash
# Check if HWP is enabled (bit 0)
sudo rdmsr -f 0:0 0x770    # 1 = HWP enabled

# What the CPU can do (capabilities)
sudo rdmsr -p 0 0x771      # e.g. 0x1102228
#   bits 7:0  = highest performance (0x28 = 40 = 4.0 GHz)
#   bits 15:8 = guaranteed (0x22 = 34 = 3.4 GHz, base clock)
#   bits 23:16 = most efficient
#   bits 31:24 = lowest

# What the OS requests
sudo rdmsr -p 0 0x774      # e.g. 0x2828
#   bits 7:0  = max performance requested
#   bits 15:8 = min performance requested
#   If both = 0x28 (40), OS is correctly asking for 4.0 GHz
```

## Step 3 — HWP Status (0x777)

```bash
sudo rdmsr -p 0 0x777
```

Bit 0 = Currently exceeding guaranteed performance
Bit 2 = Guaranteed performance changed (sticky) — the CPU detected it
- If only bit 2 is set, the CPU *was* unable to sustain its guaranteed perf at some point
- If bit 0=0 and bit 2=1, the CPU is NOT exceeding guaranteed perf even though it could — suspicious
- **Key**: if bit 2 is set, something reduced the CPU's headroom (thermal, power, VR current, or platform limit)

## Step 4 — THE KEY REGISTER: Perf Limit Reasons (0x64f)

This is the diagnostic payload. It tells you *exactly* what's limiting the CPU:

```bash
sudo rdmsr -p 0 0x64f
```

Bit assignments vary by generation but for Skylake/Kaby Lake (6th/7th gen):

| Bit | Lower 16 (Active Limit) | Upper 16 (Log) |
|-----|------------------------|----------------|
| 0   | PROCHOT                | —              |
| 1   | Thermal throttling     | Thermal log    |
| 2   | Power limit (PL1/PL2)  | Power log      |
| 3   | VR thermal alert       | VR thermal log |
| 4   | VR current limit       | VR current log |
| 5   | Package PL3            | PL3 log        |
| 6   | Amps/electrical        | Current log    |
| 12  | — (or varies)          | VR current log |

**Reading the value:**
```python
val = 0x14001000  # example
active = val & 0xFFFF
log = (val >> 16) & 0xFFFF
```

**Example decoding:**
`0x14001000` → lower 16 = `0x1000` (bit 12 = VR current LOG active), upper 16 = `0x1400` (bits 1=thermal, 10=power, 12=VR current logged)

**Common findings:**
- `0x00000000` → No limit active (should reach max turbo)
- `0x00001000` → VR current limit active (motherboard VRM bottleneck) — **most common on OEM/cheap boards**
- Bits 1 or 9 set → Thermal throttling (check cooling)
- Bits 2 or 10 set → Power limit (raise PL1/PL2)
- Bit 0 set → PROCHOT active (severe throttling)

## Step 5 — RAPL Power Limits (0x610)

If power limiting is indicated, check the current limits:

```bash
sudo rdmsr 0x610
```

Format: packed register with PL1 (bits 15:0) and PL2 (bits 47:32).

**Decoding:**
```bash
PL1_VAL=$(sudo rdmsr -f 14:0 0x610)
PL1_EN=$(sudo rdmsr -f 15:15 0x610)
PL2_VAL=$(sudo rdmsr -f 46:32 0x610)
PL2_EN=$(sudo rdmsr -f 47:47 0x610)
PL1_LOCK=$(sudo rdmsr -f 63:63 0x610)
```

Power unit = 0.125W (1/8W). So PL1=0x280 = 640 → 640 * 0.125 = 80W.

If PL1_LOCK=0, you can override:

```bash
# Raise PL2 to 125W (0x3E8 = 1000 units)
# Format: PL2_val (14 bits) | enable_bit (1) | time_window (6 bits)
# 0x3E8 | (1 << 15) | (0x3F << 16) = 0x3F83E8
PL1=$(sudo rdmsr -f 15:0 0x610)
PL2_NEW=$((0x3E8 | (1 << 15) | (0x3F << 16)))
NEW_MSR=$((PL1 | (PL2_NEW << 32)))
sudo wrmsr 0x610 $NEW_MSR
```

**Caution:** The MSR write takes effect immediately and persists until power-off. Writing insane values (>200W on a consumer board) can damage the VRM if sustained. Raise progressively (125W is safe for most decent boards).

## Step 6 — Check Active P-State Request vs Actual

```bash
sudo rdmsr -p 0 0x199   # IA32_PERF_CTL = what the OS requests
sudo rdmsr -p 0 0x198   # IA32_PERF_STATUS = what the CPU is actually running
```

Bits 15:0 encode the ratio. If CTL=0x2800 (ratio 40 = 4.0 GHz) but STATUS=0x2500 (ratio 37 = 3.7 GHz), the CPU is not delivering the requested ratio — confirms a hardware limit is active.

## Step 7 — Check for Thermal Throttling History

```bash
sudo rdmsr -p 0 0x19c   # IA32_THERM_STATUS
# bit 31: has throttled since reset (sticky)
# bit 30: currently throttling
# bits 22:16: temperature delta below TjMax (negative = hot)
```

## Root Causes (ordered by likelihood)

| Finding | Cause | Fix |
|---------|-------|-----|
| 0x64f bit 4 or 12 set | Weak motherboard VRM | Replace board, undervolt CPU, or accept lower turbo |
| 0x19c bit 31 set | Thermal throttling history | Improve cooling, clean heatsink, check fan curves |
| 0x610 PL1=65W locked | BIOS-enforced TDP limit | May require modified UEFI or hardware mod |
| No limit active but freq low | Erroneous BIOS config | Reset BIOS to defaults, check turbo/overclock settings |

## i7-6700 Reference Data

From a real tuning session (this system):

- **CPU:** i7-6700 @ 3.40GHz, 4C/8T
- **Motherboard:** "To-be-filled-by-O-E-M" (generic/OEM)
- **MSR 0x1ad:** `0x25262728` (4c=3.7, 3c=3.8, 2c=3.9, 1c=4.0)
- **MSR 0x64f:** `0x14001000` — bit 12 active, VR current limit
- **Observed max:** 3.7 GHz (all cores) — VRM can't sustain higher bins
- **All tuning applied:** governor=performance, noatime, noatime, rc.local, 99-zzzz sysctl, GRUB params
- **GPU:** RX 580 at 1411/2000 MHz, locked via `high` perf level

HWP was enabled (MSR 0x770=1), intel_pstate in active mode with performance governor. HWP_REQUEST had min=max=0x28 (40), but the VR current limit caused the CPU to cap at ratio 37 regardless of load.
