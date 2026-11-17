# Easy Effects autoload file format across versions

The autoload entry — which preset to apply to which sink automatically — uses a
filename format that has changed across EE versions and is poorly documented.
Many forum posts incorrectly claim the file is named after the device description.

## v7.1.x (Ubuntu 24.04, source-verified from `presets_manager.cpp`)

Filename: `{device_name}:{device_profile}.json`

```json
{
  "device": "alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5",
  "device-description": "Ellesmere HDMI Audio [Radeon RX 470/480 / 570/580/590] Digital Stereo (HDMI 6)",
  "device-profile": "hdmi-stereo-extra5",
  "preset-name": "Sonos Playbar + Sub"
}
```

Key path in source: `presets_manager.cpp:632` `add_autoload()`:
```cpp
output_file = autoload_output_dir / std::filesystem::path{device_name + ":" + device_profile + json_ext};
```

## v8.x (Flathub current)

Same format, no documented change. `device-description` is informational only and
never used to construct the filename.

## Why the device description makes a bad filename

Common device descriptions contain:
- `/` — e.g. "Radeon RX 470/480" (legitimate ALSA name with model line)
- `[]` — e.g. "[Radeon RX 470/480 / 570/580/590]"
- `()` — e.g. "(HDMI 6)"
- spaces, colons

These are valid JSON content but break the Linux filesystem when used as a filename.
A `/` silently splits the path and creates the file in a non-existent subdirectory.

## How to extract the right fields

```bash
# device_name and device_profile
pw-cli ls Node | grep -B1 -A30 "alsa_output.pci-0000_01_00.1" | grep -E "node.name|node.description|api.alsa.path"

# Or in JSON form
pw-dump | jq '.[] | select(.info.props["node.name"]=="alsa_output.pci-0000_01_00.1.hdmi-stereo-extra5") | .info.props | {name: ."node.name", desc: ."node.description", profile: ."device.profile.name"}'
```

## When EE silently fails to load an autoload

EE logs to `util::debug` channel (only visible with verbose logging). It compares
the autoload entry's `device` field against active node names. If the device name
has changed (e.g. after a card rename, profile change, or HDMI re-plug), the
autoload entry becomes orphaned. Re-create it with the new name.

Symptom: the filter node never appears in PipeWire for that sink. The GUI's
"Autoloading" dropdown shows nothing for that output.

## Verifying an autoload entry

After writing, restart EE or toggle the sink profile to trigger re-attach:

```bash
# restart service
systemctl --user restart app-easyeffects\\x2dservice@autostart.service

# or toggle the profile to force re-evaluation
pactl set-card-profile alsa_card.pci-0000_01_00.1 off
pactl set-card-profile alsa_card.pci-0000_01_00.1 output:hdmi-stereo-extra5
```

Then check `pw-dump | grep Filter` for the new filter node.
