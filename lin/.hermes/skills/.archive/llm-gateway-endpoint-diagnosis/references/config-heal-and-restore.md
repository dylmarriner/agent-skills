# When a config edit reverts: snapshot/heal baselines

Applies to any agent or plugin that owns your config file and "heals" it: an
assistant's plugin hooks, IDE extensions with settings sync, dotfile managers. The
mechanism is always the same shape, so the recipe transfers.

## The mechanism

1. On a session/startup hook the tool reads the live config file and stores a **baseline
   snapshot** of it — usually under the plugin's own data directory, not next to the
   config it snapshots.
2. On every subsequent start it compares live config against that baseline and **restores
   keys present in the baseline but missing live**. So an edit you make by hand is re-added
   at the next start: the edit did not fail, it was overwritten.
3. Deletions stick only when the key is **tombstoned** (recorded as deliberately removed).
   A silent delete is indistinguishable from an accident, so it gets restored.
4. The baseline is only replaced when the live file has **more** keys than the stored
   snapshot, so shrinking the live file never teaches the tool the new shape.

## Artifacts to look for

```
<plugin data dir>/<plugin>/config/settings_heal/
    highwater.json        # baseline snapshot of the whole config file
    highwater.meta.json   # key count + sorted key set + snapshot timestamp
    tombstones.json       # {"tombstoned_keys": [...]} — deletions that must stick
    heal_log.jsonl        # snapshot / restore / tombstone events, newest last
    last_healthy.json     # timestamp + key count of the last good sighting
```

Search for the directory *pattern* (`*_heal/`, `*_baseline/`, `*_restore/`) under a
plugin's data path when you do not know which plugin is doing it.

## Detection recipe

```bash
# 1. the value you removed is still in the baseline
python3 -c "import json;print(json.load(open('<heal_dir>/highwater.json')).get('<key>'))"
# 2. the snapshot mtime lines up with the last client start
stat -c '%y %n' <heal_dir>/highwater.json
# 3. the log records a restore for that key
tail -5 <heal_dir>/heal_log.jsonl
```

Confirming symptom: the key is gone right after your edit and back after the next client
run.

## Neutralization recipe (all three steps, one pass)

1. **Remove the key from the live config.** Back the file up with a timestamp first so the
   change is reversible.
2. **Remove the same key from the baseline** and refresh its metadata (`key_count`,
   `key_set`) so the two agree — a baseline that contradicts its own metadata is a new
   failure mode you do not want to debug later.
3. **Tombstone the key** in the shape the tool expects, e.g.
   `{"tombstoned_keys": ["<key>"], "updated": "<iso8601>"}`. The tombstone is what makes
   the deletion permanent; without it steps 1–2 are undone at the next start.

Verify with a **real client run** (hooks fire only there) and re-read the config: an
unchanged file after that run is the proof. Skipping this is exactly how a fix gets
diagnosed twice.

## Generalization

Whenever "the setting keeps coming back", stop editing the setting and go find the writer:

- grep the plugin/agent/extension tree for the key name, not just the config file
- look for a snapshot/baseline/restore/backup directory next to the plugin's data
- prefer the tool's own suppression mechanism (tombstone, ignore list, exclude list) over
  fighting the writer
