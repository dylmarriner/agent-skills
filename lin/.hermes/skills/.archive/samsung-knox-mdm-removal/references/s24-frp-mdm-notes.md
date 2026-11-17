# S24 SM-S921B — FRP & MDM Notes

**Firmware tested:** `S921BXXSFDZE1` (June 2025 security patch, European Exynos 2400 variant)

## USB Behavior (Same as A54)

| Mode | PID | Notes |
|------|-----|-------|
| MTP | 0x6860 | Normal boot, no ADB |
| RNDIS+DM+ACM | 0x6862 | 5 interfaces, RNDIS networking, ACM serial, no ADB |
| Download Mode | 0x685D | Exynos 2400 — same proprietary protocol as A54, heimdall incompatible |

`*#0808#` USB settings — only MTP and RNDIS+DM+ACM options. No standalone ADB. No "MTP+ADB" combo.

## Service Codes

| Code | Result |
|------|--------|
| `*#0808#` | ✓ Opens — MTP or RNDIS+DM+ACM only |
| `*#0011#` | ✓ Opens — Q-sequence CONFIRMED PATCHED on this firmware |
| `*#9900#` | ✓ Opens — Debug Level HIGH reboots phone |
| `*#*#4636#*#*` | ✗ Does nothing on this firmware |

Same behavior as A54 SM-A546E — all ADB-enable tricks dead on OneUI 6.1.

## FRP Status

S24 had FRP active after factory reset. Accessibility menu and Emergency Call available on first setup screen. TalkBack method and Alliance Shield method not tested on this firmware (user didn't proceed with the bypass during this session).

## MDM Enrollment

S24 was set up fresh from factory (no prior Miradore pre-installation detected). Setup traffic revealed DNS lookups to `api.gras.samsungdm.com` and `diagmon-serviceapi.samsungdm.com` during enrollment phase — these are Samsung DM endpoints that Miradore routes through. DNS-blocked hotspot prevented these from resolving; setup completed without MDM.

## Setup Traffic Analysis

26MB pcap captured during S24 setup on DNS-blocked hotspot. DNS queries included:
- `api.gras.samsungdm.com` (2 queries)
- `diagmon-serviceapi.samsungdm.com` (1 query)
- Zero TLS SNI for any MDM domain (no successful connections)
- Standard Android/setup domains: `update.googleapis.com`, `storage.dvs.samsungmobile.com`, `connectivitycheck.gstatic.com`
