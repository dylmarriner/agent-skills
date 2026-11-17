---
name: linux-thermal-throttling-triage
description: Diagnose a slow, hot, or throttling Linux host.
---

# Linux Thermal / Throttling Triage

Use when a Linux box feels slow, runs hot, or will not hold its clock — especially the case where CPU
and RAM look "fine" and the obvious tuning knobs are already applied. This skill decides *whether
software can help at all*. The tuning actions themselves (sysctl, service trims, compositor, Wi-Fi,
DNS) live in `linux-laptop-performance-tuning` — do not duplicate them here.

Hard rule: **never report a tuning win you did not measure.** A before/after number from step 4 is
the only acceptable evidence.

## 1. Read what the platform actually allows

```bash
cd /sys/devices/system/cpu
cat intel_pstate/no_turbo intel_pstate/max_perf_pct intel_pstate/min_perf_pct
cat cpu0/cpufreq/scaling_driver cpu0/cpufreq/scaling_governor \
    cpu0/cpufreq/scaling_max_freq cpu0/cpufreq/cpuinfo_max_freq \
    cpu0/cpufreq/energy_performance_preference
grep MHz /proc/cpuinfo
```

The tell-tale that ends the investigation early: **every core reports the identical `cpu MHz`, pinned
at the base clock and never above it.** `cpuinfo_max_freq == base` (not turbo) means `no_turbo=1` —
no core can ever boost, and no amount of sysctl tuning will fix that. Knob-by-knob table:
`references/intel-pstate-and-rapl.md`.

## 2. Find who wrote those values (inherited capping)

```bash
grep -rn -E 'no_turbo|max_perf_pct|power_limit|energy_performance' \
  /etc/systemd/system /etc/rc.local /etc/sysctl.d /etc/default /usr/local/bin 2>/dev/null
systemctl list-units --type=service --all | grep -Ei 'thermal|perf|throttle'
systemctl is-enabled <unit>; systemctl is-active <unit>
```

A hand-written "temporary thermal safety" oneshot that writes sysfs at boot is the most common root
cause of a permanently slow machine: it disables turbo, caps `max_perf_pct`, clamps RAPL and sets EPP
to `balance_power`, then outlives the crisis that created it. Fix it **in place** (edit that unit's
`ExecStart`), because two competing oneshots race and whichever runs last wins. No reboot needed:

```bash
sudo systemctl daemon-reload && sudo systemctl restart <unit> && systemctl is-active <unit>
cat /sys/devices/system/cpu/intel_pstate/no_turbo /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
```

Leave the old safety values in a comment in that unit so re-crippling is a one-line edit.

## 3. Check the power ceiling before promising gains

```bash
for f in /sys/class/powercap/intel-rapl:0/constraint_*; do echo "$(basename $f) = $(cat $f)"; done
```

`constraint_0` is long_term (PL1), `constraint_1` is short_term (PL2, the turbo burst budget).
When `constraint_0_max_power_uw == constraint_0_power_limit_uw` the firmware ceiling *is* that value
and any higher written value is silently clamped — say "nothing to gain here" rather than counting it
as a change.

## 4. Prove it with a load test (sample DURING the load)

```bash
# Foreground `&` is refused by the terminal tool. Use xargs fan-out, a backgrounded subshell
# (`for i in $(seq 8); do (timeout 12 yes >/dev/null &); done`), or a background terminal session.
seq 8 | xargs -P8 -I{} sh -c 'timeout 12 yes > /dev/null'
# in the same or a concurrent call, while it runs:
grep MHz /proc/cpuinfo | awk '{s+=$4} END{printf "%.0f avg MHz\n", s/NR}'
sensors | grep -m1 'Package id 0'
cat /proc/loadavg
```

Sampling after the load finishes proves nothing — clocks drop and temps fall immediately.

| Sustained clock under load | Verdict | Action |
|---|---|---|
| reaches the turbo range | software-capped | the aggressive tuning section applies; gains are real |
| holds base clock, ~90 °C | cooler marginal | tune, expect modest gains, watch temps |
| **below base clock**, ~98-100 °C, at the PL1 cap | thermal wall | physical fix only: clean heatsink, repaste, airflow |

## 5. When it is a thermal wall, say so

A package sitting at ~98-100 °C while the CPU cannot hold its *base* clock proves the cooler cannot
dissipate even PL1. Report exactly that, name the physical fix, and do not pad the reply with extra
knobs. Load average matters alongside the temperature: high load explains heat, but a desktop that
looks idle at 98 °C means the cooler or fan is failing.

Fan tach is frequently absent on consumer laptops (`hp-wmi-sensors` may expose only `pwm1: N/A`,
`/proc/acpi/fan/*` may not exist). With no RPM to read, do not assert a fan fault from missing sysfs —
tell the user to check exhaust airflow by hand at the vent, and treat "hot + below-base clock" as the
standing evidence.

## 6. Name the residual heat/CPU sources in the same report

- Per-process reality check: sample live, scoped load with `pidstat -u -p <candidate-PIDs> 1 3`; `ps %CPU` is a lifetime average. Avoid `pidstat -p ALL` on a busy desktop because its huge output adds avoidable load. Desktop AI/Electron stacks can hold 3-4 GB across five processes and double-digit %CPU; aggregate by command before quoting numbers. Correlate sustained CPU with temperature and sample again after diagnostics settle; a single hot reading or short-lived process spike is not proof of the sustained cause, and diagnostics themselves can briefly add load.
- Interpret memory with `MemAvailable` and `/proc/pressure/memory`, not `used` alone: reclaimable cache counts as used, while nonzero swap can be leftover from an earlier spike. Attribute current memory pressure only when available memory/pressure and active per-process RSS or `VmSwap` support it; RAM use by itself does not explain a hot CPU.
- **Name what you deliberately left alone, and why.** Once genuine misconfigurations are fixed, residual load is often the user's own stack. If explicitly asked to kill a heat source, terminate only a process proven by recent samples to be the sustained culprit; preserve active user apps/services and the current agent session unless specifically targeted. Send SIGTERM first and verify CPU load and temperature afterward. If temperatures fall while candidate processes remain active and no sustained hog is measured, do not kill them: transient diagnostics can create heat, while a hot near-idle laptop points to cooling/airflow.
- Hybrid dGPU left awake: a `runtime_status=active` AMD/NVIDIA dGPU while Intel drives the panel is
  idling heat — check `cat /sys/bus/pci/devices/<addr>/power/runtime_status`.
- When the user expects only one app to be active, inspect `pstree -ap <app-PID>` and `ps -eo pid,ppid,%cpu,etime,comm,args --sort=-%cpu | head -20` before attributing load. MCP servers, browser workers, schedulers, and Python/Node helpers launched by an agent are part of that agent's workload, not unrelated background apps; name the parent-child relationship and use fresh CPU samples before calling any process the cause.
- Boot waste that is pure nag and cheap to kill:
  `sudo systemctl disable --now ua-timer.timer ua-timer.service` (disable the **timer** too — it
  re-arms the service). Snapd auto-refreshes several times a day: `refresh.timer=monthly` is rejected
  (`not a valid weekday`), the value must be `<weekday>,HH:MM`, e.g.
  `sudo snap set system refresh.timer=sun,04:00`; verify with `snap refresh --time`.

## 7. Report shape that lands

1. Before/after table of what actually changed.
2. The measured evidence for whatever bottleneck remains (frequencies, temps, watts).
3. The rollback command for anything non-diagnostic.
4. The next step, or decide it yourself.

No menu of options, no request for permission, no prose tour of what was considered and rejected.
State the physical constraint plainly — this user wants candor and the real answer over a list of
knobs that were applied.

## Pitfalls

- **`tuned` and `power-profiles-daemon` fight over intel_pstate/EPP.** Check
  `systemctl is-active tuned power-profiles-daemon` first; use `powerprofilesctl set performance` when
  ppd owns the machine and do not install tuned beside it. `tuned-adm active` printing
  "preset profile: X" while the daemon is inactive means **nothing is applied**. Direct writes to
  `.../energy_performance_preference` can return `EBUSY` while ppd holds the interface — set the
  profile and let ppd write EPP instead of racing it from your own unit.
- **A failed tuning oneshot has usually already applied half its chain.** `bash -c` with `;` keeps
  going after an error, so a unit that exits 1 can leave `no_turbo=0` / `max_perf_pct=100` set while
  its EPP loop died — read the live sysfs values, not the unit's name or description. Make tuning
  oneshots un-failable (`|| true` per optional path, `exit 0` last) so one stale path — a PCI
  address for a removed dGPU, a device that no longer exists — cannot mark the whole profile
  `failed`, and re-check `systemctl --failed` whenever a tuned machine quietly reverts.
- **`powerprofilesctl list` marking a profile `Degraded: yes (high-operating-temperature)`** means the
  platform reports it is too hot — a thermal-wall signal, not a missing setting.
- **Under load the CPU may drop *below* base clock.** Do not explain that as a governor problem;
  check package temperature at the same moment as the frequency, always.
- **`mitigations=off` / C-state GRUB tuning is pointless on a thermally capped machine** and adds
  risk; apply it only once step 4 shows the clock is software-capped, never as a first move.

## References

- `references/intel-pstate-and-rapl.md` — intel_pstate knob table, EPP semantics, RAPL constraint
  meanings, and a known-good performance-profile systemd unit to copy.
