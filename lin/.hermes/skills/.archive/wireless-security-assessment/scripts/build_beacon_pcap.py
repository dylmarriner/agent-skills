#!/usr/bin/env python3
"""
Build a real 802.11 beacon pcap from the specification fields, so any decoder can be
cross-checked against a reference dissector on identical bytes.

This is the probe that catches wrong information-element layouts: your own fixtures encode
your own assumption and pass, while the reference decoder reads the same bytes differently.

Usage
-----
    python3 build_beacon_pcap.py --out /tmp/beacon.pcap --ssid LAB --channel 6 --wps
    tshark -r /tmp/beacon.pcap -V | sed -n '/Tag: Vendor Specific/,/^$/p'   # WSC elements
tshark -r /tmp/beacon.pcap -T fields -E separator=/t \
    -e wlan.bssid -e wlan.ssid -e wlan.ds.current_channel \
    -e wlan.rsn.akms.type -e wlan.rsn.capabilities \
    -e wps.version -e wps.wifi_protected_setup_state -e wps.ap_setup_locked \
    -e wps.selected_registrar_config_methods -e wps.device_name

A frame that dissects with zero "Unknown Type" entries and returns every field is built
correctly: use it as the oracle for your own parser and require the two to agree field by
field. Write the file to a world-readable temp dir (e.g. /tmp) - a reference dissector can
refuse a path inside a restricted tree even for a file the calling user owns.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

# LINKTYPE_IEEE802_11 (802.11 without radiotap/FCS)
DLT_IEEE802_11 = 105


def element(element_id: int, body: bytes) -> bytes:
    """802.11 information element: id(1) length(1) body."""
    return bytes([element_id, len(body)]) + body


def wsc_element(element_type: int, value: bytes) -> bytes:
    """WSC data element: type(2, network order) length(2, network order) value."""
    return element_type.to_bytes(2, "big") + len(value).to_bytes(2, "big") + value


def wps_ie(locked: bool = False, methods: int = 0x0084, name: str = "LabAP", state: int = 0x02) -> bytes:
    """WSC information element body (after the 00:50:F2 04 header): TLV list, Version first."""
    elements = [
        (0x104A, b"\x10"),                       # Version 1.0
        (0x1044, bytes([state])),                 # Wifi Protected Setup State
        (0x1057, bytes([1 if locked else 0])),    # AP Setup Locked
        (0x1053, methods.to_bytes(2, "big")),     # Selected Registrar Config Methods
        (0x1012, (0x0004).to_bytes(2, "big")),    # Device Password ID
        (0x103B, b"\x01"),                       # Response Type
        (0x1011, name.encode()),                  # Device Name
        (0x1021, b"Ralink"),                      # Manufacturer
        (0x1004, (0x0004).to_bytes(2, "big")),    # Authentication Type Flags
        (0x1010, (0x0008).to_bytes(2, "big")),    # Encryption Type Flags
    ]
    return b"".join(wsc_element(t, v) for t, v in elements)


def rsn_ie(akms, caps: int = 0x0040, pairwise=(4,), group: int = 4) -> bytes:
    """RSN element body (802.11-2020 9.4.2.24): version, group, pairwise, AKM, capabilities."""
    body = bytearray((1).to_bytes(2, "little") + bytes([0x00, 0x0F, 0xAC, group]))
    body += len(pairwise).to_bytes(2, "little")
    for suite in pairwise:
        body += bytes([0x00, 0x0F, 0xAC, suite])
    body += len(akms).to_bytes(2, "little")
    for suite in akms:
        body += bytes([0x00, 0x0F, 0xAC, suite])
    body += caps.to_bytes(2, "little")
    return bytes(body)


def beacon(bssid: str, ssid: str, channel: int, akms, caps: int, with_wps: bool, ht_primary=None) -> tuple:
    """Return (frame_bytes, [(element_id, body), ...]) for a beacon frame."""
    mac = bytes.fromhex(bssid.replace(":", ""))
    header = b"\x80\x00" + b"\x00\x00" + b"\xff" * 6 + mac + mac + b"\x00\x00"
    fixed = b"\x00" * 8 + b"\x64\x00" + b"\x11\x04"  # timestamp, beacon interval, capability
    elements = [
        (0, ssid.encode()),
        (1, bytes([0x82, 0x84, 0x8B, 0x96, 0x0C, 0x12, 0x18, 0x24])),
    ]
    if ht_primary is None:
        elements.append((3, bytes([channel])))
    else:
        elements.append((61, bytes([ht_primary, 0x01, 0x00, 0x00, 0x00, 0x00])))
    elements.append((48, rsn_ie(akms, caps=caps)))
    if with_wps:
        elements.append((221, b"\x00\x50\xf2\x04" + wps_ie()))
    return header + fixed + b"".join(element(i, b) for i, b in elements), elements


def write_pcap(path: Path, frames) -> Path:
    """Write frames as a libpcap file (LINKTYPE_IEEE802_11)."""
    blob = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, DLT_IEEE802_11)
    for frame in frames:
        blob += struct.pack("<IIII", 0, 0, len(frame), len(frame)) + frame
    path.write_bytes(blob)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build a real 802.11 beacon pcap for decoder cross-checking")
    parser.add_argument("--out", default="/tmp/beacon.pcap", help="output pcap path (use a world-readable dir)")
    parser.add_argument("--bssid", default="aa:bb:cc:11:22:33")
    parser.add_argument("--ssid", default="SCYTHE-LAB")
    parser.add_argument("--channel", type=int, default=6)
    parser.add_argument("--akm", default="2,8", help="AKM suite types: 2=PSK, 8=SAE, 1=802.1X, 11=192-bit")
    parser.add_argument("--caps", default="0x0040", help="RSN capabilities: 0x0040 MFPC, 0x0080 MFPR")
    parser.add_argument("--wps", action="store_true", help="include a WSC information element")
    parser.add_argument("--ht-channel", type=int, help="emit HT Operation instead of DS Parameter Set")
    args = parser.parse_args(argv)

    akms = [int(part) for part in args.akm.split(",") if part.strip()]
    frame, elements = beacon(args.bssid, args.ssid, args.channel, akms, int(args.caps, 16), args.wps, args.ht_channel)
    path = write_pcap(Path(args.out), [frame])
    print(f"wrote {path} ({path.stat().st_size} bytes, {len(frame)}-byte frame)")
    print(f"elements: {[i for i, _ in elements]}")
    print("cross-check with:")
    print(f"  tshark -r {path} -V | sed -n '/Tag: Vendor Specific/,/^$/p'")
    print(
        f"  tshark -r {path} -T fields -E separator=/t -e wlan.bssid -e wlan.ssid "
        "-e wlan.ds.current_channel -e wlan.rsn.akms.type -e wlan.rsn.capabilities "
        "-e wps.version -e wps.wifi_protected_setup_state -e wps.selected_registrar_config_methods"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
