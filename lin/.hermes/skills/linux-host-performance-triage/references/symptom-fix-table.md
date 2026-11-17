# Symptoms → Checks → Fixes

Lookup table for a Linux desktop/server that "feels slow". Order matters: work top-down, because the earlier rows cause the later ones.

| Symptom | Check | Fix |
|---|---|---|
| Everything feels sluggish, load average low | `scaling_cur_freq` vs `cpuinfo_max_freq`; `energy_performance_preference`; `powerprofilesctl get` | Set the vendor power profile (`powerprofilesctl set performance`). A governor of `powersave` on `intel_pstate` is normal — EPP is the real knob. |
| A custom perf/tuning systemd unit sits in `--failed` | `systemctl status <unit> -l`; `systemctl cat <unit>` | Read the ExecStart for the real error. One failing sysfs path marks the whole oneshot failed, so every later write in it silently never runs — guard each write, per-command `|| true`, and end with `exit 0`. |
| Boot takes many seconds longer than it should | `systemd-analyze blame`; `systemd-analyze` totals | Chase only offenders that are not merely waiting on a dependency. A network mount that fails and retries is the usual winner. |
| Any access to a mount path stalls, then errors | `findmnt`; `systemctl status <path>.mount`; `df` | Stale fstab entry: add `nofail,x-systemd.automount` plus a short `x-systemd.device-timeout`. Confirm the export exists before assuming a connection problem — `mount error(2)` = share name not found, `error(101)` = host unreachable. |
| `grub-editenv: invalid environment block` in the journal | `journalctl -u <grub unit>`; `grub-editenv /boot/grub/grubenv list` | Back up, then `grub-editenv <path> create` and `unset recordfail`. A stale `recordfail` can hold the boot menu open. |
| Fast for a minute, then slows under load | `sensors`; `scaling_cur_freq` during a short load | Thermal ceiling. Confirm with a 4-thread load test; if it pins near `crit`, the sustained limit is physical, not configuration. Leave the documented way back. |
| Swap in use, memory "full" | `free -h`; per-process `VmSwap` from `/proc/<pid>/status` | With zram, swap in use is normal. Find the few real consumers and report them; do not kill the user's own tooling (agents, containers, editors) to move a number. |
| Disk nearly full | `df -h` on real filesystems; reclaimable counts from the container engine | Report headroom and reclaimable space as separate numbers. Do not run aggressive prune/`-a` variants against images or volumes that may be wanted. |
| Concerned about I/O | `/proc/pressure/io` (`some` vs `full`) | `some` rising while `full` stays near zero is scheduling latency, not a saturated device. Quote both numbers before blaming the disk. |

## Port and process checks

- A listening port can look dead if the listener list was truncated with `head`. Filter the full `ss -ltn` output, or probe the port directly: `000`/refused = nothing listening, `401`/`403` = alive and requiring auth.
- Full boot timing is firmware + loader + kernel + userspace. Quote the split; userspace alone is usually the only part you can change.
