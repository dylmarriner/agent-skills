#!/usr/bin/env python3
"""OpenHuman Integration Engine - Social media & 118+ app integrations via Composio.
Coded directly into Hermes. Run 'setup' first to authenticate services.
Usage:
  python3 integrations.py setup              # First-time setup (install deps, show login steps)
  python3 integrations.py apps               # List available apps
  python3 integrations.py connect <app>       # Connect an app (opens OAuth in browser)
  python3 integrations.py list-connections    # Show connected apps
  python3 integrations.py execute <app> <action> <params>  # Execute an action
  python3 integrations.py social feed         # Fetch social media feed from connected apps
  python3 integrations.py social post <text>  # Post to connected social platforms
"""
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = HOME / ".hermes" / "openhuman"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def ensure_composio():
    """Ensure composio-core is installed."""
    r = subprocess.run(["pip3", "list", "--format=columns"], capture_output=True, text=True)
    if "composio-core" not in r.stdout:
        print("Installing composio-core...")
        subprocess.run(["pip3", "install", "--break-system-packages", "composio-core"], check=True)
    print("✓ composio-core installed")

def cmd_setup():
    ensure_composio()
    print()
    print("=== OpenHuman Integration Setup ===")
    print()
    print("To connect social media & 118+ apps:")
    print()
    print("1. Get a free Composio API key:")
    print("   https://app.composio.dev/")
    print()
    print("2. Set your API key:")
    print("   export COMPOSIO_API_KEY=your_key_here")
    print("   composio login --no-browser")
    print()
    print("3. Connect apps (one-time OAuth per app):")
    print("   composio add facebook     # Facebook/Pages")
    print("   composio add messenger    # Messenger")
    print("   composio add instagram    # Instagram")
    print("   composio add gmail        # Gmail")
    print("   composio add slack        # Slack")
    print("   composio add github       # GitHub")
    print("   composio add whatsapp     # WhatsApp")
    print("   composio add telegram     # Telegram")
    print()
    print("Each opens your browser for OAuth. Login once, done.")
    print()

def cmd_apps():
    ensure_composio()
    r = subprocess.run(["composio", "apps"], capture_output=True, text=True)
    print(r.stdout)

def cmd_connect():
    app = sys.argv[2] if len(sys.argv) > 2 else ""
    if not app:
        print("Usage: integrations.py connect <appname>")
        sys.exit(1)
    r = subprocess.run(["composio", "add", app], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr)

def cmd_list_connections():
    ensure_composio()
    r = subprocess.run(["composio", "connections"], capture_output=True, text=True)
    print(r.stdout)

def cmd_execute():
    if len(sys.argv) < 5:
        print("Usage: integrations.py execute <app> <action> <json_params>")
        sys.exit(1)
    app = sys.argv[2]
    action = sys.argv[3]
    params = sys.argv[4]
    ensure_composio()
    r = subprocess.run(["composio", "execute", app, action, params], capture_output=True, text=True)
    print(r.stdout)

def cmd_social():
    sub_cmd = sys.argv[2] if len(sys.argv) > 2 else "feed"
    ensure_composio()
    
    # Check which social apps are connected
    r = subprocess.run(["composio", "connections"], capture_output=True, text=True)
    connected = r.stdout.lower()
    
    social_apps = ["facebook", "messenger", "instagram", "twitter", "linkedin"]
    available = [a for a in social_apps if a in connected]
    
    if sub_cmd == "feed":
        if not available:
            print("No social media apps connected yet.")
            print("Run: composio add facebook")
            print("Run: composio add messenger")
            print("Run: composio add instagram")
            return
        for app in available:
            print(f"Fetching feed from {app}...")
            r2 = subprocess.run(["composio", "execute", app, "get_feed", "{}"], capture_output=True, text=True, timeout=30)
            if r2.stdout:
                print(r2.stdout[:500])
    
    elif sub_cmd == "post":
        text = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "Hello from OpenHuman + Hermes!"
        for app in available:
            print(f"Posting to {app}...")
            params = json.dumps({"message": text, "content": text})
            r2 = subprocess.run(["composio", "execute", app, "post", params], capture_output=True, text=True, timeout=30)
            print(r2.stdout[:500])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    cmds = {
        "setup": cmd_setup,
        "apps": cmd_apps,
        "connect": cmd_connect,
        "list-connections": cmd_list_connections,
        "execute": cmd_execute,
        "social": cmd_social,
    }
    if cmd in cmds:
        cmds[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
