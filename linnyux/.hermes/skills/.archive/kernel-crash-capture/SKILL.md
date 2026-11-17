---
name: kernel-crash-capture
description: Use when a host dies with no logs; arm netconsole.
---

# Kernel Crash Capture (out-of-band)

A host that loses power or wedges writes nothing to its own disk: journald's tail dies with the
unclean shutdown, rsyslog stops mid-file, and promtail never flushes — so the crash leaves no evidence
on the machine itself. The fix is to get kernel messages OFF the box while it is healthy, over UDP,
from the kernel. Then the next death is a readable record instead of a guess.

Pair this with log-based crash analysis (panics, OOM, GPU ring timeouts, D-state hangs) when the host
did log something. This skill is for the case where it logged nothing.

## Trigger conditions

- "It just shut off by itself", "screen froze and I had to hold the power button", "why did it crash,
  there's nothing in the logs"
- Journal for the dead boot ends mid-routine with no `Stopping ...`/`systemd-shutdown` sequence
- Repeated unexplained unclean boots over weeks
- Pre-emptively: any host that has died silently once will likely do it again — arm capture

## Step 1 — Establish that it really was a hard stop

Do this before any hardware theory. If the machine stopped cleanly, capture is unnecessary and the
cause is in the logs.

```bash
last -x reboot shutdown | head -20    # a "shutdown system down" record == clean stop
last -Fx | head -25                   # per session "- crash" == no logout/shutdown record written
journalctl --list-boots | tail -10    # last entry of the dead boot == moment of death
journalctl -b 0 -k | grep -Ei "uncleanly|recovery complete|corrupted"
```

Unclean end confirmed by any of: no shutdown record in wtmp, `systemd-journald: File ... corrupted or
uncleanly shut down`, `EXT4-fs (sdX): recovery complete` on the next boot. A clean `poweroff` always
leaves a full stop sequence, so "it ended with no shutdown sequence" rules out every software actor —
including the suspicious cron job you just noticed.

Recover the last seconds from the second log sink before it is overwritten:

```bash
grep -E "2026-09-24T18:4[3-7]" /var/log/syslog | grep -viE "promtail|openclaw" | tail -70
```

**Pitfall:** `/var/log/syslog` lines are ISO-8601 (`2026-09-24T18:46:01.928054+12:00`) while
`journalctl` prints `Sep 24 18:46:01`. Grepping syslog with the journal's `^Sep 24 18:4` prefix matches
nothing and reads as "no data" — use the ISO prefix.

Sanity-check that no crash file exists before concluding "nothing survived":
`ls -la /sys/fs/pstore/ /var/crash/ /var/lib/systemd/coredump/` and `systemctl is-active kdump-tools`
(no crash kernel = no vmcore will ever exist).
**Pitfall:** `dmidecode -t 15,23` (SEL / System Reset) is empty on consumer boards — that absence proves
nothing about how the machine stopped.
**Pitfall:** never `journalctl | grep` across all boots; multi-GB journals blow a 120-180 s timeout.
Scope every query with `-b <n>`, `-k`, or `--since/--until`.

## Step 2 — Arm the collector (an always-on machine on the same L2)

```bash
sudo apt-get install -y socat
```

`/etc/systemd/system/netconsole-listen.service`:

```ini
[Unit]
Description=Netconsole listener (captures remote kernel logs)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/socat -u UDP-RECV:6666,reuseaddr -
StandardOutput=append:/var/log/netconsole-<sender>.log
StandardError=append:/var/log/netconsole-<sender>.log
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now netconsole-listen.service
ss -lunp | grep 6666
sudo ufw allow from <sender-lan-ip> to any port 6666 proto udp comment "netconsole from <sender>"
```

A default-deny firewall (ufw, or iptables `-P INPUT DROP`) silently swallows the datagrams — scope the
rule to the sender's address, never `Anywhere`.

## Step 3 — Arm the sender

```bash
sudo LOCAL_IP=<sender-ip> LOCAL_IF=<iface> REMOTE_IP=<collector-ip> scripts/netconsole-arm.sh
printf 'kernel.hardlockup_panic=1\nkernel.printk = 8 4 1 7\n' | sudo tee /etc/sysctl.d/99-crash-capture.conf
sudo sysctl -q -p /etc/sysctl.d/99-crash-capture.conf
```

Persist through reboots with a `Type=oneshot`, `RemainAfterExit=yes` unit running the arm script after
`network-online.target`, `ExecStop` = `echo 0 > /sys/kernel/config/netconsole/target1/enabled`.

**Pitfall (costs the most time):** `netcon0` registers with console level 3, so anything at level 4
(`echo test > /dev/kmsg`) is silently dropped and the whole chain looks broken. `kernel.printk = 8 4 1 7`
opens the gate; panics and watchdog traces print at KERN_EMERG and pass either way, but oopses, errors
and warnings need the raise. There is no per-target/module `loglevel` knob on modern kernels —
`ls /sys/module/netconsole/parameters/` shows only `oops_only`, so do not chase modprobe options.

## Step 4 — Verify, do not assume

```bash
cat /proc/consoles | grep netcon0
echo "<0>NETCONSOLE-PROBE $(date -Is)" | sudo tee /dev/kmsg >/dev/null
sleep 2
ssh <collector> 'tail -5 /var/log/netconsole-<sender>.log'
```

`netcon0` must be listed as an attached console AND the KERN_EMERG probe must land in the collector's
file. **Pitfall:** a successful `nc -u` only proves network + firewall; it says nothing about whether
the kernel console is attached, so test both layers separately.

## Step 5 — Read the death

| Collector log shows | Verdict |
|---|---|
| Panic / oops / lockup / NMI watchdog trace | Wedge with evidence — decode the trace |
| Routine lines, then nothing at a timestamp, no trace | Instant power loss — the kernel never got to speak |
| Full `Stopping ...` shutdown sequence | The stop was software-initiated after all |

The last line's timestamp is the death certificate. Correlate it with the dying host's final journal
entry, and check a second machine on the same LAN/subnet for uptime spanning the death window: if a
peer stayed up, house power did not drop and the fault is inside that chassis.

Dying at idle (load ~0, no logged user activity for minutes before) points at deep-C-state rail collapse
rather than load-induced instability — first check PSU and BIOS `Power Supply Idle Control = Typical
Current Idle`, then dGPU runtime-PM (`amdgpu.runpm=0` test), then DRAM above the CPU's rated speed
(`memtest86+`, already in `/boot`).

## Step 6 — Teardown

```bash
sudo sh -c 'echo 0 > /sys/kernel/config/netconsole/target1/enabled'
sudo rmdir /sys/kernel/config/netconsole/target1     # only after disabling
sudo systemctl disable --now netconsole-remote.service   # sender
sudo systemctl disable --now netconsole-listen.service   # collector
```

Leave it armed on any host that has already died silently — the cost is one UDP datagram per kernel
message.

## Adjacent traps that cost evidence

- **A host systemd service and its containerized twin sharing a state directory**: when the container
  mounts that directory `rw` and runs as root, it recreates state files `root:root 600` and the host
  service crash-loops forever on `permission denied` — `chown` never sticks. Check mounts before
  chowning anything: `docker inspect <c> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} (rw={{.RW}}){{"\n"}}{{end}}'`.
- **Duplicate workload against a host service on the same port** shows as `docker ps` ->
  `Restarting (1) N seconds ago` churning on a fixed cadence with `bind: address already in use` in
  `docker logs`: it can never succeed. `docker stop` + `docker update --restart=no` instead of debugging it.
- **Confirm a log-shipping target exists before blaming the shipper**: a shipper retries a dead endpoint
  forever while its local file errors mask the real story — check the endpoint answers
  (`curl -s -o /dev/null -w '%{http_code}' http://<host>:<port>/ready`) and that the target host is
  present on the network before touching configs.

## Support files

- `references/netconsole-remote-capture.md` — full recipe: configfs walkthrough, units, the loglevel and
  MAC-resolution traps, acceptance probe, teardown.
- `scripts/netconsole-arm.sh` — re-runnable arming script (`REMOTE_IP` required; `LOCAL_IP`/`LOCAL_IF`
  default to the default-route interface).
