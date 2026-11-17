#!/usr/bin/env python3
"""Instantaneous per-process CPU usage, measured as a two-sample /proc delta.

Why this exists: `ps %CPU` is a LIFETIME average over the process's whole life.
A daemon that spiked once an hour ago still reads 60%, and one currently pegging
a core reads low immediately after it restarts. Neither answers "what is using
CPU right now", which is the question that matters before you remove anything.

Usage:
    cpu-snapshot.py [interval_seconds] [top_n]     # defaults: 10s, top 10
    cpu-snapshot.py --self-test
"""

import glob
import os
import sys
import time

CLK_TCK = os.sysconf('SC_CLK_TCK')
CORES = os.cpu_count() or 1


def parse_stat(text):
    """Return (utime + stime in ticks, comm) from a /proc/<pid>/stat line.

    The comm field is wrapped in parens and MAY ITSELF CONTAIN SPACES AND PARENS
    (e.g. a thread named "weird (name) here"). Split on the LAST ')' or every
    field index shifts and you silently read the wrong counters.

    Kernel field numbering: field 3 = state, field 14 = utime, field 15 = stime.
    After splitting on the last ')', parts[0] is field 3, so field N is parts[N-3].
    """
    lp = text.find('(')
    rp = text.rfind(')')
    if lp < 0 or rp < lp:
        return None
    name = text[lp + 1:rp]
    parts = text[rp + 2:].split()
    try:
        return (int(parts[11]) + int(parts[12]), name)
    except (IndexError, ValueError):
        return None


def sample():
    """pid -> (cpu ticks, comm) for every process we can read."""
    out = {}
    for path in glob.glob('/proc/[0-9]*/stat'):
        try:
            with open(path) as fh:
                parsed = parse_stat(fh.read())
        except OSError:
            continue  # process exited between the glob and the open
        if parsed is not None:
            out[path.split('/')[2]] = parsed
    return out


def report(interval, top_n):
    before = sample()
    time.sleep(interval)
    after = sample()

    ticks = sum(max(0, after[p][0] - before[p][0]) for p in before if p in after)
    print('total CPU busy: %.1f%% of %d cores' % (ticks / CLK_TCK / interval / CORES * 100, CORES))

    rows = []
    for pid, (now, name) in after.items():
        if pid in before and now > before[pid][0]:
            rows.append(((now - before[pid][0]) / CLK_TCK / interval * 100, name, pid))
    rows.sort(reverse=True)
    if not rows:
        print('  (no process consumed CPU during the sample window)')
    for pct, name, pid in rows[:top_n]:
        print('  %6.1f%%  %s (pid %s)' % (pct, name, pid))


def self_test():
    # comm containing spaces AND parens must not shift the field indices
    line = '1234 (weird (name) here) S 1 2 3 4 5 6 7 8 9 10 999 888'
    assert parse_stat(line) == (999 + 888, 'weird (name) here'), parse_stat(line)
    # a plain name must still land on the same indices
    assert parse_stat('42 (bash) S 1 2 3 4 5 6 7 8 9 10 7 3') == (10, 'bash')
    # malformed input returns None instead of raising
    assert parse_stat('garbage') is None
    assert parse_stat('1 (unclosed') is None
    print('cpu-snapshot: self-test OK')


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    else:
        report(
            float(sys.argv[1]) if len(sys.argv) > 1 else 10.0,
            int(sys.argv[2]) if len(sys.argv) > 2 else 10,
        )
