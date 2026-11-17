# Tool dialects: verified argv and output facts

Every entry below was checked against the tool's own help/manpage or against real captured
output. Re-verify on the target host before trusting any of it: the wireless toolchain changes
its interfaces between minor versions, and a wrong flag fails *silently* (tool exits, empty
capture, misleading finding).

## Discovery formula

```
<tool> --help | head -40          # the option set of THIS build
man <tool>                        # semantics, incl. what a filter actually affects
```

For reference decoders, introspect instead of remembering:

```
tshark -G fields  | awk -F'\t' '{print $3}' | grep '^wlan\.rsn\.'   # real field names
tshark -G values  | grep -A20 'wps.type'                             # real value tables
```

## airodump-ng

CSV header (15 columns, index 0..14, stable across versions):
`BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication,
Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key`
Station section header (7 columns): `Station MAC, First time seen, Last time seen, Power,
# packets, BSSID, Probed ESSIDs`

- Prefer mapping columns by header name when the header is present (a reordering then cannot
  silently mis-map); keep the documented fixed order as the fallback.
- ESSIDs are written **unquoted**, so an SSID containing a comma splits the row - rejoin the
  tail instead of taking `row[13]` blindly.
- Live handshake detection: the header/stdout carries `WPA handshake: <BSSID>`; the CSV alone
  cannot tell you a handshake landed.
- `--band a` = 5 GHz, `b`/`g` = 2.4 GHz (combine as `abg`); `-c <ch>` pins a channel;
  `--write <prefix>` emits `<prefix>-01.csv` / `-01.cap`; `--write-interval 1` for live rows.
- The CSV cannot express PMF capability or WPS attributes - a beacon pass is required.

## wash / reaver / bully

- `wash -i <mon> [-c <ch>]` - the WPS table goes to **stdout** (`BSSID Ch dBm WPS Lck Vendor
  ESSID`). There is **no text-output option** in the current lineage (`-O` writes a pcap, `-o`
  does not exist). Read stdout.
- `reaver -i <mon> -b <bssid> [-c <ch>] -vv -N -d 1`: `-N` = no NACKs, `-K` = pixie dust
  (**takes no argument**), `-p <pin>` = single pin, `-g <n>` = stop after n attempts (use it to
  make an engagement attempt budget bind inside the tool), `-L` = ignore AP lock-out (avoid;
  respecting lock-out is the safer default).
- Progress lines differ by lineage; parse all real spellings:
  `[+] Starting Cracking Session. Pin count: 0, Max pin attempts: 11000`,
  `[+] Pin count advanced: 10001. Max pin attempts: 11000`,
  `[+] Pin count: 42 of 11000 (0.38%)`, `[+] Trying pin 12345670.`
  Output is cumulative: the **last** `Trying pin` is the current attempt. Failing to parse the
  counter silently disables whatever budget decrements from it.
- Success: `[+] WPS PIN: '...'`, `[+] WPA PSK: '...'`, `[+] AP SSID: '...'`.
  Lock-out: `AP Setup Locked`, `Detected AP rate limiting`.
- `bully`: probe `-h` for the pixie-dust spelling before passing it; treat it as the alternate
  engine, not the default.

## hcxdumptool (capability matrix - the big one)

| Build | Status display | Target filter | Notes |
| --- | --- | --- | --- |
| <= 6.2.9 "old style" | `--enable_status=N` | `--filterlist_ap=<file>` + `--filtermode=2` (6.0.0+; earlier `--filterlist=`) | |
| >= 6.3.0 rewrite | `--enable_status` **removed**; display always on, `--rds=1` to keep it | user-space lists replaced by kernel BPF: `--bpfc="<pcap filter>"` generates, `--bpf=<file>` loads | passing a removed option makes it exit without capturing |

```
# discover, then construct
hcxdumptool --help | grep -E 'enable_status|rds|filterlist|filtermode|bpfc|bpf|tot|error_max|disable_deauthentication'
hcxdumptool --bpfc="wlan addr1 AA:BB:CC:DD:EE:FF or wlan addr2 ... or wlan addr3 ..."   # -> decimal program
tcpdump -i <mon> wlan addr3 AA:BB:CC:DD:EE:FF -ddd                                      # fallback generator
```

- Always pass `--disable_deauthentication` when the build supports it: its internal deauth
  flood cannot be counted against a frame budget, so the counted injection path (aireplay-ng)
  must be the only source of deauthentication frames.
- `--filtermode=2` is the *target* list (1 = protection list) and affects **outgoing
  interaction only** - the capture is still broadband, so hash material must be post-filtered.
- Conversion: `hcxpcapngtool -o out.22000 -E essidlist <capture>` (reads pcap and pcapng);
  `hcxpcaptool` is the legacy name.

## airmon-ng / iw

- `airmon-ng start <iface>` layouts to parse: `monitor mode enabled on <mon>` and
  `monitor mode vif enabled for [phyX]<iface> on [phyX]<iface>mon`.
- Monitor-mode preference order: dedicated vif (`iw phy <phy> interface add <n> type monitor`)
  -> in place (`ip link set <iface> down`; `iw dev <iface> set type monitor`; up) -> `airmon-ng`
  (which kills NetworkManager/wpa_supplicant - record what it stopped and restart it on
  teardown).
- `iw dev` reports the phy as a bare number (`phy#0` -> `0`) but `iw phy` wants `phy0`: prefix
  it. `iw phy <phy> info` frequencies may print as `2412.0 MHz` - accept the decimal.
- 5 GHz channelisation runs to 5905 MHz (ch 181-184); 5925 MHz is where 6 GHz starts.
- `iw dev <iface> scan` prints RSN/WPS blocks in human-readable form; older builds dump hex.
  Handle both.

## hashcat (mode 22000)

- `hashcat -m 22000 <hashfile> -a 0 <wordlist> [-r rules] --potfile-path <p> --status --status-timer 10`;
  `-a 3 <mask>` (+ `--increment`) for masks. On a VM without a working OpenCL runtime it exits
  `4` - `--force` is the documented workaround.
- Exit codes: 0 cracked, 1 exhausted, 2 aborted, 3 checkpoint quit, 4 runtime error. **The
  potfile is the source of truth**, never the exit code: read the potfile and verify the key.
- `Recovered.....` counts digests; `Progress.....` counts keyspace positions - different
  numbers, keep them in different fields.
- Potfile lines `hash:password` may contain `:` in the password: split once.

## tshark as a capture agent for beacons

```
tshark -i <mon> -l -q -a duration:N -T fields -E separator=/t \
  -e wlan.fc.type_subtype -e wlan.bssid -e wlan.ssid -e wlan.ds.current_channel \
  -e wlan.rsn.version -e wlan.rsn.gcs.type -e wlan.rsn.pcs.type -e wlan.rsn.akms.type \
  -e wlan.rsn.capabilities -e wlan.tag.number -e wlan.tag.length \
  -e wps.version -e wps.wifi_protected_setup_state -e wps.ap_setup_locked \
  -e wps.selected_registrar_config_methods -e wps.device_password_id -e wps.response_type \
  -e wps.device_name -e wps.manufacturer -e wps.primary_device_type -e wps.rf_bands
```

- Field names above come from `tshark -G fields`; `wps.*` is populated for the WSC elements,
  `wlan.wfa.ie.wps.*` does not exist in current builds.
- `wlan.ssid` prints as **hex** (`FT_BYTES`) in current builds and as text in older ones.
  Disambiguate deterministically with the SSID element's declared length from
  `wlan.tag.number` / `wlan.tag.length`: a hex dump is exactly twice that length.
- `wlan.tag.data` is empty for tags a sub-dissector handles (RSN, WPS) - read the dissected
  `wlan.rsn.*` / `wps.*` fields instead of hoping for raw IE bytes.
- `wlan.fc.type_subtype` for a beacon prints as `0x0008` (also accept `8`, `0x08`).
- Don't pass `-I` when the interface is already in monitor mode.
