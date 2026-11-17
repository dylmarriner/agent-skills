# rabuntu Hermes Editable Path Fix — 2026-07-27

## Symptom

```
$ hermes version
Traceback:
  PermissionError: [Errno 13] Permission denied: '/root/.hermes/hermes-agent/hermes_cli/__init__.py'
```

Machine: rabuntu@100.68.0.96 (Pi 5, Raspberry Pi OS)
User: rabuntu (no sudo for `pip3 install` unless with --break-system-packages)

## Root Cause

```
$ pip3 show hermes-agent
Editable project location: /root/.hermes/hermes-agent
```

Hermes was installed as root with `pip install -e /root/.hermes/hermes-agent/`. The editable finder at `/usr/local/lib/python3.11/dist-packages/__editable___hermes_agent_0_17_0_finder.py` hardcodes `/root/.hermes/hermes-agent/` paths in MAPPING and NAMESPACES dicts. User rabuntu can't stat any path under `/root/`.

## Fix Applied

1. Copy source to rabuntu-accessible location:
```
sudo cp -a /root/.hermes/hermes-agent /home/rabuntu/.local/share/hermes-agent
sudo chown -R rabuntu:rabuntu /home/rabuntu/.local/share/hermes-agent
```

2. Patch editable finder (replace path in MAPPING + NAMESPACES dicts):
```
sudo sed -i 's|/root/\.hermes/hermes-agent/|/home/rabuntu/.local/share/hermes-agent/|g' \
  /usr/local/lib/python3.11/dist-packages/__editable___hermes_agent_0_17_0_finder.py
```

3. Verify:
```
$ hermes version
Hermes Agent v0.17.0 (2026.6.19) · upstream 208f0d7c
Project: /home/rabuntu/.local/share/hermes-agent
Python: 3.11.2
OpenAI SDK: 2.24.0
Up to date
```

## Additional Notes

- The sed only changed paths in the MAPPING and NAMESPACES dict strings — no structural changes needed.
- PEP 668 was enforced on this Pi (Raspberry Pi OS), preventing `--break-system-packages` reinstall as a workaround.
- No venv existed; the fix preserved the system-wide editable install semantics.
- `sudo` was only needed for the cp + chown + sed — the user can now run `hermes` without sudo.
