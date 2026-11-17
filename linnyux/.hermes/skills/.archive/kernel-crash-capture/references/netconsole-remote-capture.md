# Out-of-band kernel capture (netconsole -> a second LAN machine)

Why: a machine that dies by power loss or a full wedge writes nothing to its own disk. Promtail, Loki,
journald and rsyslog all fail for that case because they are userspace and their last writes never
flush. Nothing logged means nothing to read later, so arm this while the box is healthy.

Topology: sender (machine that dies) -> UDP netconsole to a collector on the same L2 segment. Keep the
sender's link up; netconsole runs from the kernel at emergency level.

## Collector setup (the always-on box)

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
rule to the sender's LAN address, never `Anywhere`.

## Sender setup (the machine under watch)

Run `scripts/netconsole-arm.sh` from this skill (`LOCAL_IP`/`LOCAL_IF` optional, `REMOTE_IP` required),
or do it by hand:

```bash
sudo modprobe netconsole
sudo mkdir -p /sys/kernel/config/netconsole/target1
cd /sys/kernel/config/netconsole/target1
echo <local-ip>   | sudo tee local_ip
echo 6666         | sudo tee local_port
echo <iface>      | sudo tee dev_name
echo <remote-ip>  | sudo tee remote_ip
echo 6666         | sudo tee remote_port
echo <remote-mac> | sudo tee remote_mac
echo 1            | sudo tee enabled
```

Persist with a `Type=oneshot`, `RemainAfterExit=yes` unit that runs after `network-online.target`,
`ExecStart` = the arm script, `ExecStop` = `echo 0 > /sys/kernel/config/netconsole/target1/enabled`.

Harden so a lockup reports instead of black-screening:

```bash
printf 'kernel.hardlockup_panic=1\nkernel.printk = 8 4 1 7\n' | sudo tee /etc/sysctl.d/99-crash-capture.conf
sudo sysctl -q -p /etc/sysctl.d/99-crash-capture.conf
```

## Traps (each one cost real time)

1. **Level filter drops everything below KERN_ERR.** `netcon0` registers with console level 3, so a
   plain `echo test > /dev/kmsg` (level 4) is silently discarded and the whole chain looks broken.
   Raise it with `kernel.printk = 8 4 1 7`. Verified by sweeping levels 1..7: 1-3 arrived before the
   change, level 4 arrived after. Panics and watchdog traces print at KERN_EMERG and pass either way,
   but oopses, errors and warnings need the raise.
2. **There is no per-target or module `loglevel` knob on modern kernels.**
   `ls /sys/module/netconsole/parameters/` shows only `oops_only`; do not chase `/etc/modprobe.d`
   options or per-target attributes that do not exist.
3. **`ip neigh` field positions shift with and without `dev`.** `ip neigh show <ip>` prints
   `<ip> dev <if> lladdr <mac> STATE` (mac = field 5); `ip neigh show <ip> dev <if>` prints
   `<ip> lladdr <mac> STATE` (mac = field 3). A hardcoded `awk '{print $5}'` yields an empty MAC and the
   arm step aborts with "cannot resolve ... MAC". Parse by pattern instead:
   `ip neigh show <ip> | grep -oE '([0-9a-f]{2}:){5}[0-9a-f]{2}' | head -1`, after `ping -c1` to populate
   the neighbour entry (retry a few times — an absent entry right after boot is normal).
4. **`nc -u` succeeding does not prove netconsole is attached.** Test the layers separately: raw UDP
   proves network + firewall, a KERN_EMERG probe proves the kernel console.
5. **Verify attachment, not just config:** `cat /proc/consoles` must list `netcon0`.

## Verification (run it, do not assume)

```bash
cat /proc/consoles | grep netcon0
echo "<0>NETCONSOLE-PROBE $(date -Is)" | sudo tee /dev/kmsg >/dev/null
sleep 2
ssh <collector> 'tail -5 /var/log/netconsole-<sender>.log'
```

The KERN_EMERG probe appearing in the collector's file is the acceptance test.

## Reading the result after a death

| Collector log shows | Verdict |
|---|---|
| Panic / oops / lockup / NMI watchdog trace | Wedge with evidence — decode the trace |
| Routine lines, then nothing at a timestamp, no trace | Instant power loss — the kernel never got to speak |
| Full `Stopping ...` shutdown sequence | The stop was software-initiated after all |

The last line's timestamp is the death certificate — correlate it with the dying machine's final journal
entry and with peer machines' uptime to separate a chassis fault from a mains event.

## Teardown

```bash
sudo sh -c 'echo 0 > /sys/kernel/config/netconsole/target1/enabled'
sudo rmdir /sys/kernel/config/netconsole/target1      # only after disabling
sudo systemctl disable --now netconsole-remote.service   # sender
sudo systemctl disable --now netconsole-listen.service   # collector
```
