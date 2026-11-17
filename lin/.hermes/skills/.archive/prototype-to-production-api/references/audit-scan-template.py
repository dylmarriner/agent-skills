"""
Placeholder detection scanner for prototype code audit.
Run in execute_code against the target directory.
"""
import os, re

bad_patterns = {
    'time.sleep': r'time\.sleep\(',
    'placeholder_tag': r'placeholder|stub|mock|fake|dummy',
    'unimplemented': r'NotImplementedError',
    'todo': r'TODO|FIXME|HACK|XXX',
    'rfc1918': r'(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})',
}

def audit_file(fpath):
    with open(fpath, encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    lines = content.split('\n')
    findings = []
    for i, line in enumerate(lines, 1):
        for label, pat in bad_patterns.items():
            if re.search(pat, line, re.IGNORECASE):
                findings.append((i, label, line.strip()[:120]))
    # File-level flags
    flags = []
    sleeps = re.findall(r'time\.sleep\(', content)
    if len(sleeps) >= 3:
        flags.append(f"{len(sleeps)}x time.sleep() calls")
    if re.search(r"return\s*\{[^}]*'status'[^}]*\}", content):
        flags.append("Static mock return data")
    return findings, flags
