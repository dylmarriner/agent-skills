#!/usr/bin/env python3
"""
Config merge helper for Hermes config restore.

Usage:
    python3 references/config-merge-restore.py ~/.hermes/config.yaml

Merges key settings from a Hermesconfig-style restore into an existing config.yaml.
Run this INSTEAD of replacing config.yaml with a template.
"""

import yaml
import sys
import os


def merge_config(config_path: str) -> None:
    """Merge standard Hermesconfig restore settings into an existing config.yaml."""
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # --- Settings from Hermesconfig template ---
    config.setdefault("display", {})["show_cost"] = True
    config.setdefault("memory", {})["provider"] = "honcho"
    config.setdefault("compression", {})["threshold"] = 0.95
    config.setdefault("compression", {})["target_ratio"] = 0.2
    config.setdefault("cron", {})["wrap_response"] = True

    # Wire the prefill file (if it exists at standard path)
    prefill_path = os.path.expanduser("~/.hermes/prefill.json")
    if os.path.exists(prefill_path):
        config["prefill_messages_file"] = prefill_path

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Merged Hermesconfig settings into {config_path}")
    print("  - display.show_cost = True")
    print("  - memory.provider = honcho")
    print("  - compression.threshold = 0.95, target_ratio = 0.2")
    print("  - cron.wrap_response = True")
    print("  - prefill_messages_file = ~/.hermes/prefill.json (if exists)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        config_path = os.path.expanduser("~/.hermes/config.yaml")
    else:
        config_path = sys.argv[1]
    merge_config(config_path)
