---
name: ios-activation-bypass-diagnostics-linux
description: Diagnostic workflow for iOS activation-locked devices on Linux. Covers USB detection, libimobiledevice pairing, DNS bypass, recovery mode, and realistic hardware limitations by chip generation. Use when a user wants to check or attempt iCloud activation bypass on an iPhone connected to a Linux machine.
---

# iOS Activation Bypass Diagnostics (Linux)

Systematic approach to diagnosing and attempting iCloud activation bypass on a connected iPhone from a Linux machine.

## Prerequisites

```bash
sudo apt install -y libimobiledevice-utils libimobiledevice-dev usbmuxd ideviceinstaller ifuse irecovery
```

## Step 1: Detect Device

```bash
# Check USB enumeration
lsusb | grep -E "05ac"

# Product IDs by mode:
#   0x12a8 = normal mode (locked/activation screen)
#   0x1281 = recovery mode
#   0x1227 = DFU mode

# Try libimobiledevice
idevice_id -l

# If usbmuxd is dead:
sudo killall usbmuxd 2>/dev/null
sudo usbmuxd -f -v &  # background
sleep 2
idevice_id -l
```

## Step 2: Pair and Get Info

```bash
# Pair - look for "SUCCESS"
idevicepair pair

# Get device info
ideviceinfo -k ProductType     # e.g. iPhone14,7
ideviceinfo -k ProductVersion  # e.g. 18.2.1
ideviceinfo -k ActivationState # Unactivated = locked
ideviceinfo -k BrickState      # true = at Hello/setup screen
ideviceinfo -k CPUArchitecture # arm64e = A12+
```

## Step 3: Determine Hardware Exploitability

| Chip | Devices | checkm8? | Notes |
|------|---------|----------|-------|
| A5-A11 | iPhone 4s through X | Yes | checkra1n works |
| A12-A13 | iPhone XR through 11 | No | No public bootrom exploit |
| A14-A18 | iPhone 12 through 16 Pro | No | SEP is hardware-isolated |
| M1+ | iPad Pro/Air | No | Same limitations |

**For iPad-specific model → chip → checkm8 compatibility, see `references/ipad-checkm8-compatibility.md`.** That reference covers all standard iPad, Pro, Air, and mini generations with exact chips and exploit status.

iPhone14,7 = iPhone 14 Plus = A15 = **not checkm8 compatible**.

## Step 4: Attempt Recovery Mode

```bash
# Software method (only works if lockdownd responds)
udid=$(idevice_id -l | head -1)
ideviceenterrecovery "$udid"

# Check if it switched to recovery mode (USB re-enumerates)
lsusb | grep -E "05ac"
# If still 0x12a8 = didn't work

# If recovery mode achieved:
irecovery -q    # query device
irecovery -n    # reboot
```

**Pitfall:** `ideviceenterrecovery` often says "Failed" then "switching" but actually doesn't work on bricked devices. If lockdownd isn't fully responding, the command is a no-op.

## Step 5: Test DNS Bypass Servers

The classic DNS bypass uses custom DNS on the phone's WiFi to redirect Apple's activation server (`albert.apple.com`).

```bash
# Check if known bypass servers are alive
dig @104.238.180.120 albert.apple.com +short
dig @45.55.28.166 albert.apple.com +short
dig @104.155.28.90 albert.apple.com +short
dig @45.33.32.156 albert.apple.com +short

# Compare with normal resolution
dig @8.8.8.8 albert.apple.com +short
```

**Pitfall:** Most public DNS bypass servers for iCloud are dead or unreliable. If they don't respond, the DNS method won't work. The servers listed in old files/tutorials (104.238.180.120, 45.55.28.166) are likely offline.

## Step 6: Set Up Local DNS Proxy (Alternative)

```bash
# Install dnsmasq
sudo apt install -y dnsmasq

# Create config to redirect Apple activation servers
cat << EOF | sudo tee /etc/dnsmasq.d/apple-bypass.conf
address=/albert.apple.com/YOUR_SERVER_IP
address=/gs.apple.com/YOUR_SERVER_IP
no-resolv
server=8.8.8.8
server=1.1.1.1
interface=YOUR_WIFI_IFACE
bind-interfaces
EOF

sudo systemctl restart dnsmasq
```

**Note:** This only works if `YOUR_SERVER_IP` actually hosts a server that responds with a valid activation success response. Pointing to 127.0.0.1 yields connection refused.

## Step 7: DNS Bypass Instructions (User on Phone)

If the phone is at the Hello/activation screen:

1. Connect to any WiFi network
2. Tap the (i) icon next to the network name
3. Scroll to DNS section, set Manual
4. Enter a working bypass DNS IP
5. Go back — activation should redirect and skip the iCloud check

## What Won't Work on Modern iPhones

- **checkm8** — only A5-A11 (iPhone X and older)
- **Software-based recovery mode entry** — doesn't work on bricked/unactivated devices
- **iRemoval Pro / paid tools** — client is just a shell, the actual bypass is server-side; even they don't support recent iOS
- **PyUSB low-level attacks** — need sudo/root, and modern USB stacks have protections
- **Brute force** — SEP hard-blocks after 10 wrong attempts, wipes after 10 more

## Verification Points

```bash
# Device detected on USB
lsusb | grep "05ac"

# Device paired
idevicepair validate

# Info accessible
ideviceinfo -k ProductType

# Context
echo "Model + iOS version + checkm8 compatibility determine what's possible"
echo "For iPhone 14+ / iOS 18+: only Apple can remove the activation lock"
