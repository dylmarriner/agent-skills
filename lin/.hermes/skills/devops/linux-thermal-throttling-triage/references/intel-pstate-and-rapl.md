# intel_pstate knobs, EPP, RAPL, and a known-good profile unit

## intel_pstate sysfs

| Path | Values | Effect |
|---|---|---|
| `/sys/devices/system/cpu/intel_pstate/no_turbo` | 0 / 1 | 1 disables Turbo Boost entirely; `cpuinfo_max_freq` collapses to base |
| `.../intel_pstate/max_perf_pct` | 0-100 | hard ceiling on achievable clock as % of turbo max |
| `.../intel_pstate/min_perf_pct` | 0-100 | floor; a low value is fine and lets cores idle down |
| `.../cpu0/cpufreq/scaling_driver` | intel_pstate | HWP; the `powersave` governor alongside it is normal and scales fine |
| `.../cpu0/cpufreq/scaling_max_freq` | kHz | effective ceiling; compare against `cpuinfo_max_freq` |
| `.../cpu0/cpufreq/cpuinfo_max_freq` | kHz | platform max; equal to base ⇒ turbo is off |
| `.../cpu0/cpufreq/energy_performance_preference` | performance / balance_performance / balance_power / power | latency-vs-power ramp bias; `balance_performance` for interactive work |

Quick verdicts:

- All cores reporting the identical `cpu MHz` at the base clock = `no_turbo=1` or a `max_perf_pct` cap.
- `scaling_max_freq` far above current clocks with cores idling low = healthy.
- EPP `balance_power` on an interactive machine = slower ramp on every wakeup.

Writes go to every policy:

```bash
for p in /sys/devices/system/cpu/cpufreq/policy*; do echo balance_performance > "$p/energy_performance_preference"; done
```

## RAPL constraints (/sys/class/powercap/intel-rapl:0/)

| File | Meaning |
|---|---|
| `constraint_0_name` / `constraint_1_name` | `long_term` (PL1) / `short_term` (PL2) |
| `constraint_0_power_limit_uw` | sustained package wattage cap |
| `constraint_0_max_power_uw` | firmware maximum; if equal to the limit, raising it is a no-op |
| `constraint_1_power_limit_uw` | burst budget (often 40+ W) with a millisecond `time_window_us` |

PL1 is what a sustained workload settles at; PL2 only buys short bursts. A machine pinned at PL1 with a
hot package is cooling-limited — raising PL1 will not help even where headroom exists.

## Known-good performance-profile unit

Turbo on, full perf range, EPP biased for interactive use. `After=` the profile managers so this wins at
boot; the thermal-safety values stay in a comment for a one-line rollback. Edit an existing inherited
unit in place rather than adding a second one — competing oneshots race.

```ini
[Unit]
Description=Performance profile (turbo enabled, EPP balance_performance)
After=multi-user.target power-profiles-daemon.service thermald.service

[Service]
Type=oneshot
# Rollback to thermal-safety state: no_turbo=1, max_perf_pct=70, EPP balance_power.
ExecStart=/bin/bash -c 'echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo; \
  echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct; \
  for p in /sys/devices/system/cpu/cpufreq/policy*; do \
    [ -e "$p/energy_performance_preference" ] && echo balance_performance > "$p/energy_performance_preference"; \
  done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart <unit> && systemctl is-active <unit>
# verify it landed, do not assume:
cat /sys/devices/system/cpu/intel_pstate/no_turbo /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
```

## Sampled counters worth capturing in the report

```bash
sensors | grep -E 'Package id 0|Core 0'          # package + core temps, crit usually 100 °C
cat /sys/class/power_supply/BAT*/capacity; on_ac_power
cat /proc/loadavg                                # read WITH the temperature, not alone
sensors | grep -Ei 'pch|nvme'                    # secondary heat sources (PCH, SSD)
for h in /sys/class/hwmon/hwmon*; do echo "$(cat $h/name): $(ls $h | grep -c fan) fan inputs"; done
```
