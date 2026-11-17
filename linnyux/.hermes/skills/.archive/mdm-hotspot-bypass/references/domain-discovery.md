# MDM Domain Discovery via Traffic Analysis

Complete domain list discovered through live tcpdump/tshark capture during Samsung setup wizard. Captured 2026-07-13 on SM-S921B (S24) and SM-A546E (A54).

## Full Domain Blocklist

```
# Miradore enrollment gateway (Azure hosted)
address=/gateway.miradore.com/0.0.0.0
address=/gateway.miradore.com/::
address=/miradore.com/0.0.0.0
address=/miradore.com/::

# Samsung Device Management API
address=/samsungdm.com/0.0.0.0
address=/samsungdm.com/::
address=/api.gras.samsungdm.com/0.0.0.0
address=/api.gras.samsungdm.com/::
address=/diagmon-serviceapi.samsungdm.com/0.0.0.0
address=/diagmon-serviceapi.samsungdm.com/::
address=/dir-apis.samsungdm.com/0.0.0.0
address=/dir-apis.samsungdm.com/::

# Samsung Global Service Logic
address=/samsunggsl.com/0.0.0.0
address=/samsunggsl.com/::
address=/gsl.samsunggsl.com/0.0.0.0
address=/gsl.samsunggsl.com/::
address=/eu-gslu.samsunggsl.com/0.0.0.0
address=/eu-gslu.samsunggsl.com/::

# Samsung B2B certificate pinning
address=/secb2b.com/0.0.0.0
address=/secb2b.com/::
address=/pinning-02.secb2b.com/0.0.0.0
address=/pinning-02.secb2b.com/::

# Microsoft Azure (Miradore CDN/data/telemetry)
address=/mobile.pipe.aria.microsoft.com/0.0.0.0
address=/mobile.pipe.aria.microsoft.com/::
address=/mobile.events.data.microsoft.com/0.0.0.0
address=/mobile.events.data.microsoft.com/::
```

## Traffic Analysis Methodology

### Step 1: Capture DNS queries during setup
```bash
sudo tshark -r phone_traffic.pcap -Y "dns.flags.response == 0" \
  -T fields -e dns.qry.name | sort -u
```

Look for ANY domains with `samsungdm`, `samsunggsl`, `secb2b`, `miradore`, `knox`, `mdm`, `manage`, `aria.microsoft`, etc.

### Step 2: Check TLS SNI for connected servers
```bash
sudo tshark -r phone_traffic.pcap -Y "tls.handshake.extensions_server_name" \
  -T fields -e tls.handshake.extensions_server_name | sort -u | sort -rn
```

This shows servers the phone SUCCESSFULLY established TLS with. Any MDM-related SNI here means the DNS block is incomplete.

### Step 3: Check destination IPs for non-Google/CDN traffic
```bash
sudo tshark -r phone_traffic.pcap -T fields -e ip.dst | sort | uniq -c | sort -rn | head -20
```

Look for unusual IPs (not Google 142.250.x, not Akamai 2.x/3.x/23.x). Cross-reference with known Azure CDN ranges (13.x, 20.x, 40.x, 52.x).

### Step 4: Check for DNS failures
```bash
sudo tshark -r phone_traffic.pcap -Y "dns.flags.response == 1 and dns.flags.rcode != 0" \
  -T fields -e dns.qry.name -e dns.flags.rcode | sort -u
```

If domains appear here with NXDOMAIN/SERVFAIL, dnsmasq might not be handling them correctly.

## Miradore Log Analysis

The Miradore app writes logs to `/sdcard/Android/data/com.miradore.client.v2/files/miradore.log.0`:

### Key Lines

```
Miradore Online client v.X.Y.Z (build NNN)
Management type         : Normal
Instance GUID           : Not set          ← Not yet enrolled
Client GUID             : Not set          ← Not yet enrolled
```

```
Device is currently connected to a network: true/false
ConnectionTask#doInBackground(), opening connection
Client not yet registered, registering before sending INVENTORY message
Adding authentication headers to REGISTER message, authId=<UUID>
sendMessage(), request type: REGISTER
```

```
Error while sending a REGISTER message to server, errorType=NETWORK_ERROR
Unable to resolve host "gateway.miradore.com": No address associated with hostname
Sessions statistics: Successful sessions: 0, Failed sessions: N
client registration failed
```

```
onReceive(), action=android.app.action.DEVICE_ADMIN_ENABLED    ← Local admin active
Admin does not have KNOX_APP_MGMT permission                    ← No Knox access
Admin does not have KNOX_EXCHANGE permission                    ← No exchange access
SAFE not enabled on the device                                  ← No Samsung SAFE
```

## SMS/Content Provider Exfiltration

Miradore's exfiltration framework accesses these providers (log evidence):
- `content://com.android.contacts/data` — Contacts
- `content://sms/inbox` — SMS messages
- `content://com.samsung.android.auth/account` — Samsung account data
- `/data/misc/wifi/wpa_supplicant.conf` — WiFi passwords
- `/data/misc/keystore/user_0/` — Keystore
