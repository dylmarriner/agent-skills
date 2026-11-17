#!/usr/bin/env python3
"""Prove a read-only ECU collector's guard refuses writes, with no adapter attached.

    python verify_readonly_guard.py path/to/collector.py
    python verify_readonly_guard.py path/to/collector.py --guard guard

Imports the module and then:
  1. structural  - ALLOWED_READ_SIDS and FORBIDDEN_WRITE_SIDS (if the module declares them) must
                   not intersect;
  2. behavioural - guard() must refuse every known write service, including the key-send half of
                   security access (0x27, even sub-function);
  3. behavioural - guard() must not refuse the read samples the module declares as permitted.

Exit 0 only when nothing leaked. Run it from the repo root with the project's own interpreter so
relative imports resolve. This is the evidence that a "0 writes" claim is real: a boundary that has
never been executed is a comment.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

# Service -> a syntactically plausible frame. Session control, reset, clear-DTC, routines and the
# download/transfer block are all state changes or writes even though none of them look like one.
WRITE_PROBES = {
    0x10: b"\x10\x03",                          # session control (unlocks seeds/security/DIDs)
    0x11: b"\x11\x01",                          # ECU reset
    0x14: b"\x14\xff\xff\xff",                  # clear DTC
    0x27: b"\x27\x02\x11\x22\x33\x44",          # security access, KEY SEND
    0x28: b"\x28\x01\x01",                      # communication control
    0x2E: b"\x2e\xf1\x90\x00",                  # write data by identifier
    0x2F: b"\x2f\xf1\x90\x03\x01",              # input/output control
    0x31: b"\x31\x01\x02\x03",                  # routine control
    0x34: b"\x34\x00\x44\x00\x00\x00\x00\x10",  # request download
    0x36: b"\x36\x01",                          # transfer data
    0x37: b"\x37",                              # request transfer exit
    0x3B: b"\x3b\x01",                          # write data by address
    0x3D: b"\x3d\x01",                          # write memory by address
}

READ_PROBES = {
    0x01: b"\x01\x0c",
    0x03: b"\x03",
    0x09: b"\x09\x02",
    0x19: b"\x19\x02\xff",
    0x22: b"\x22\xf1\x90",
    0x23: b"\x23\x14\x00\x00\x00\x00\x10",
    0x27: b"\x27\x01",                          # requestSeed: reads ECU state, burns no attempt
    0x3E: b"\x3e\x00",
}


def load(path: Path):
    spec = importlib.util.spec_from_file_location("collector_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collector", type=Path, help="path to the read-only collector module")
    parser.add_argument("--guard", default="guard", help="guard callable name (default: guard)")
    args = parser.parse_args()

    module = load(args.collector)
    guard = getattr(module, args.guard)
    allowed = getattr(module, "ALLOWED_READ_SIDS", None)
    forbidden = getattr(module, "FORBIDDEN_WRITE_SIDS", None)
    failures: list[str] = []

    if allowed and forbidden and (allowed & forbidden):
        failures.append(
            f"LEAK structural: allowed and forbidden sets overlap on "
            f"{sorted('0x%02X' % s for s in allowed & forbidden)}"
        )

    for sid, frame in sorted(WRITE_PROBES.items()):
        try:
            guard(frame)
        except Exception as exc:  # any raise is a boundary; report anything unexpected by name
            note = "" if isinstance(exc, PermissionError) else f" ({type(exc).__name__})"
            print(f"ok  refused 0x{sid:02X}{note}")
        else:
            failures.append(f"LEAK write service 0x{sid:02X} passed the guard")

    for sid, frame in sorted(READ_PROBES.items()):
        if allowed is not None and sid not in allowed:
            print(f"--  skipped 0x{sid:02X} (module does not declare it permitted)")
            continue
        try:
            guard(frame)
        except Exception as exc:
            failures.append(
                f"OVER-BLOCK 0x{sid:02X} is a declared read but the guard raised {type(exc).__name__}"
            )
        else:
            print(f"ok  allowed 0x{sid:02X}")

    for line in failures:
        print(line)
    print("FAIL" if failures else "PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
