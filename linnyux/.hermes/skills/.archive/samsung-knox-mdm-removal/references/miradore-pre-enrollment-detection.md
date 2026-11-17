# Miradore Pre-Enrollment Detection & A54 USB Probing

**Session date:** 2026-07-13
**Device:** Samsung SM-A546E (Exynos 1380)
**MDM Agent:** Miradore Online Client v2.18.8 (build 468)
**State:** Pre-enrollment (WiFi off, registration failing with NETWORK_ERROR)

## USB Descriptors

### MTP Mode (PID 0x6860)
```
Interface 0 (MTP):     class=0x06(Imaging), bulk 81 IN, 01 OUT, int 82 IN
Interface 1 (CDC Ctrl): class=0x02(Comm), subclass=0x02, prot=0x01 — AT commands
                        interrupt 84 IN only
Interface 2 (CDC Data): class=0x0a(CDC Data), bulk 83 IN, 02 OUT
```

The CDC ACM serial is accessible at `/dev/ttyACM0` — it talks to the modem CPU, not the AP. All traffic is proxied through PACM (AP-side gatekeeper).

### Download Mode (PID 0x685D)
```
Interface 0 (CDC Ctrl): class=0x02(Comm), subclass=0x02, prot=0x01
                        interrupt 82 IN (max=10)
Interface 1 (CDC Data): class=0x0a(CDC Data), bulk 81 IN, 01 OUT
```

No ACM serial available in download mode — cdc_acm driver doesn't auto-bind to the download mode interface (no IAD in descriptor).

## AT Command Probing Results

| Command | Response | Meaning |
|---------|----------|---------|
| `AT` | `OK` | Basic handshake |
| `AT+SWATD=0` | `[DR]: CHANGE TO DDEXE` / `[ATD]: CHANGE TO DDEXE` | Modem → Download/Dev EXE mode |
| `AT+SWATD=1` | `[DR]: CHANGE TO ATD` / `[ATD]: CHANGE TO ATD` | Modem → AT Data mode |
| `AT+SWATD=2` | `[DR]: ATD` + `ERROR` | Already in ATD |
| `AT+SWATD=0,0` through `=0,3` | CHANGE TO DDEXE then ERROR | SWATD takes single param only |
| `AT+SWATD=?` | `PACM(AP),UNREGISTED` | Range query blocked |\n| `AT+SWATD=0` + USB reset | Mode stays 0x6860 MTP | DDEXE is modem-internal only, not USB gadget |
| `AT+SWAT=1` | `PACM(AP),UNREGISTED` | SWAT blocked by AP |
| `AT+ADBENABLE=1` | `PACM(AP),UNREGISTED` | ADB enable blocked |
| `AT+USBADB=1` | `PACM(AP),UNREGISTED` | USB ADB blocked |
| `AT+DEBUGLVC=0,5` | `PACM(AP),PROTECTED_NO_TOK` | Needs auth token |
| `AT+CGSN` | `PACM(AP),NOT_ALLOWED_CRO` | Cross-op blocked |
| `AT+SSW=2` | `PACM(AP),UNREGISTED` | SSW blocked |
| `AT+DUMPCTRL=1,0` | (blank - no error, no OK) | Accepted but no response |
| `AT+CGMR` | `ERROR` | Firmware query denied |
| `AT+CLAC` | `ERROR` | List commands denied |
| `AT+CRSM=...` | (hangs serial) | SIM command hangs |
| `AT+CPIN?` | (hangs serial) | PIN check hangs |

### PACM Error Codes
- `PACM(AP),UNREGISTED` — Feature not registered on AP side (most common on stock firmware)
- `PACM(AP),PROTECTED_NO_TOK` — Feature exists but needs authorization token
- `PACM(AP),NOT_ALLOWED_CRO` — Cross-operation restriction

## Miradore Log Analysis

**Full log path:** `Internal storage/Android/data/com.miradore.client.v2/files/miradore.log.0`

**Device info block:**
```
Miradore Online client v.2.18.8 (build 468)
IMEI                    : 000000000000000  (masked — not registered)
WiFi MAC                : 02:00:00:00:00:00  (masked)
Serial number           : -
Android ID              : 1c099239f95f8b73
Model                   : SM-A546E
Firmware                : Android 14
Current UTC time        : 2026-07-12 19:57:14
```

**Enrollment XML** (extracted from log):
```xml
<Message>
  <EnrollmentKey><![CDATA[ba7a5bc2-4927-42d9-a988-57b9345f9f71]]></EnrollmentKey>
  <ForceAuthentication><![CDATA[false]]></ForceAuthentication>
  <PublicKey><![CDATA[-----BEGIN PUBLIC KEY-----
  ...]]></PublicKey>
</Message>
```

**Registration failures** (repeated every ~10s):
```
Error while sending a REGISTER message to server, errorType=NETWORK_ERROR
java.net.UnknownHostException: Unable to resolve host "gateway.miradore.com"
```

**Failed sessions counter:**
```
Sessions statistics
    Succesfull sessions: 0
    Failed sessions:   3+
```

**Security state indicators:**
```
Not Work Profile or Fully Managed  ← enrollment not complete
Admin does not have KNOX_APP_MGMT  ← no Knox admin yet
SAFE not enabled on the device      ← Knox SAFE not active
```

## Download Mode Protocol Testing

**Heimdall 1.4.2:**
```
$ heimdall print-pit --no-reboot
ERROR: Failed to send handshake! ERROR: Protocol initialisation failed!
```

Heimdall's control transfer handshake (`0x42/0x64 bRequest`) fails with pipe errors on Exynos 1380. The device doesn't respond to the expected ODIN protocol requests.

**pyusb bulk endpoint probing:**
- `set_configuration()` succeeds
- `claim_interface(dev, 1)` succeeds (CDC Data interface)
- Bulk endpoints 0x01 OUT, 0x81 IN found and accessible
- Sending `b'ODIN\0'` returned `4c 4f 4b 45` (ASCII "LOKE") — ONE TIME only, not reproducible after USB reset
- All subsequent `ep_out.write()` → `ep_in.read()` attempts timed out
- Interrupt endpoint 0x82 (CDC ACM notification) never has pending data
- Device is alive and accepting interface claims, but the protocol handshake is undocumented/unknown

The bootloader is clearly active (accepts configuration, claims interfaces) but the command protocol is not the old ODIN used by heimdall. Without documented protocol or reverse-engineered traffic captures, download mode is a dead end for Linux tools on 2024+ Samsung Exynos.

## RNDIS Mode (PID 0x6862) via `*#0808#`

**USB descriptor:** `rndis_acm_dm` — 5 interfaces, 1 configuration.

```
Interface 0: RNDIS Communications Control (Wireless class)
Interface 1: RNDIS Ethernet Data (CDC Data)
Interface 2: CDC ACM Control (Communications, Abstract/Modem, AT)
Interface 3: CDC ACM Data
Interface 4: Vendor Specific Class (0xFF), Subclass 16, Protocol 1 — debug/DM
```

**Network behavior:**
- PC receives DHCP lease on `192.168.69.0/24` (typically `.218` or `.xxx`)
- Gateway/default route: `192.168.69.234` — this is the phone
- Pingable (TTL=64, ~2ms latency)
- **No open TCP/UDP ports** — nmap scan of 1-10000 found nothing
- `adb connect 192.168.69.234:5555` → "Connection refused"
- No SSH, no HTTP, no other services

The RNDIS interface is a USB Ethernet gadget for tethering — it gives the phone internet access through the PC, not the other way around. The phone runs no server-side services on this interface.

**ACM serial in RNDIS mode:** /dev/ttyACM0 present but owned by root:dialout (mode 660). The lin user needs `sudo chmod 666 /dev/ttyACM0` or group membership fix. AT command behavior is identical to MTP mode — same PACM proxy.

## Hostapd / NM Interaction Notes

- `hostapd` is installed by `apt-get install hostapd` but does NOT need manual config when using `nmcli dev wifi hotspot`.
- NM creates a hotspot connection named "Hotspot" and manages hostapd internally.
- Restarting NM (`systemctl restart NetworkManager`) disconnects the current WiFi and reconnects to the previous known network (e.g. "ORBI14"). After NM restart, always re-enable with `nmcli connection up Hotspot`.
- The `ipv4.dns-options` on the Hotspot NM connection can also carry `address=/domain/0.0.0.0` entries, but this is harder to manage than files in `dnsmasq-shared.d/`.
- To clear stale DNS configs: delete all `block-*.conf` from both `dnsmasq.d/` AND `dnsmasq-shared.d/`, clear `ipv4.dns-options` with `nmcli connection modify Hotspot ipv4.dns-options ""`, then restart NM.

## Tools Referenced

- **Heimdall v1.4.2** — installed via apt, works on S2-S9 era, NOT on Exynos 1380
- **go-mtpfs** — MTP FUSE mount for Android file access
- **pyusb** — Python USB library for raw endpoint communication
- **NetworkManager (nmcli)** — Hotspot creation + dnsmasq DNS blocking

## TLS SNI Traffic Capture Results

After setting up the DNS-blocked hotspot and connecting the phone, captured traffic revealed hidden MDM infrastructure domains via TLS SNI extraction:

```
# TLS SNI domains found by tshark
gmscompliance-pa.googleapis.com         # Google Play compliance (5 hits)
dir-apis.samsungdm.com                  # Samsung Device Management API
gsl.samsunggsl.com                      # Samsung Global Service Logic
eu-gslu.samsunggsl.com                  # EU region GSL
pinning-02.secb2b.com                   # Certificate pinning
auditrecording-pa.googleapis.com        # Android Enterprise audit
digitalassetlinks.googleapis.com         # App verification
app-measurement.com                     # Analytics
```

### Key Finding: Samsung DM Infrastructure

The Miradore MDM on Samsung devices routes through Samsung's own device management infrastructure:
- `dir-apis.samsungdm.com` (Samsung Device Management API)
- `gsl.samsunggsl.com` / `eu-gslu.samsunggsl.com` (Global Service Logic)

These domains are **not blocked** by only blocking `gateway.miradore.com`. The phone uses Samsung DM as the enrollment proxy.

### IPv6 Bypass

**Critical finding:** dnsmasq's `address=/domain/0.0.0.0` only blocks IPv4 A records. The phone falls back to **IPv6 AAAA records** and still reaches the MDM server:

```
gateway.miradore.com → many-to-one: 2603:1061:14:1a::1 (IPv6, NOT blocked)
```

This is why the initial DNS block appeared to work (Miradore registration failed) but the MDM still enrolled — the enrollment may have gone through Samsung DM over IPv6.

**Both IPv4 and IPv6 must be blocked:**
```
address=/domain/0.0.0.0    # blocks A records
address=/domain/::         # blocks AAAA records
```

## Updated Hotspot Config (IPv6 + Full Domain Block)

Final working dnsmasq config:

```
address=/gateway.miradore.com/0.0.0.0
address=/gateway.miradore.com/::
address=/miradore.com/0.0.0.0
address=/miradore.com/::
address=/samsungdm.com/0.0.0.0
address=/samsungdm.com/::
address=/dir-apis.samsungdm.com/0.0.0.0
address=/dir-apis.samsungdm.com/::
address=/gsl.samsunggsl.com/0.0.0.0
address=/gsl.samsunggsl.com/::
address=/eu-gslu.samsunggsl.com/0.0.0.0
address=/eu-gslu.samsunggsl.com/::
address=/pinning-02.secb2b.com/0.0.0.0
address=/pinning-02.secb2b.com/::
```

Verify block with:
```bash
nslookup gateway.miradore.com 10.42.0.1     # → 0.0.0.0 AND ::
nslookup dir-apis.samsungdm.com 10.42.0.1   # → 0.0.0.0 AND ::
```

## NetworkManager + dnsmasq Debug

NM's hotspot mode runs its OWN dnsmasq — the process command line looks like:
```bash
/usr/sbin/dnsmasq --conf-file=/dev/null --no-hosts ... --conf-dir=/etc/NetworkManager/dnsmasq-shared.d
```

Key flags:
- `--conf-dir=/etc/NetworkManager/dnsmasq-shared.d` — this is the ONLY directory read by NM's hotspot dnsmasq
- `--bind-interfaces --except-interface=lo --listen-address=10.42.0.1`
- `--dhcp-range=10.42.0.10,10.42.0.254,60m`

Hotspot:
- SSID: `MDM-Bypass`
- Password: `bypass1234`
- Subnet: `10.42.0.0/24`
- PC IP: `10.42.0.1`
- DNS: NetworkManager dnsmasq with `/etc/NetworkManager/dnsmasq-shared.d/block-miradore.conf`

DNS block rules:
```
address=/gateway.miradore.com/0.0.0.0
address=/miradore.com/0.0.0.0
address=/mdm.miradore.com/0.0.0.0
address=/api.miradore.com/0.0.0.0
```
