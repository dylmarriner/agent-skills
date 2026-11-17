#!/usr/bin/env python3
"""
Reference: source-implementation-audit session script
Audited 92 original sources in archive/original_sources/ against 715+ .py files.
Methodology and class mapping extracted from that session.
"""

import subprocess, re, os

def grep_class(term):
    """Check if class exists in workspace via live grep."""
    r = subprocess.run(
        f"cd /home/lin/Documents/MUTS && grep -rn '^class.*{term}' "
        f"--include='*.py' . 2>/dev/null | grep -v '/archive/' "
        f"| grep -v '/backend-archive-' | wc -l",
        shell=True, capture_output=True, text=True, timeout=10
    )
    return int(r.stdout.strip())

# Helper to produce workspace class list
# cd /path/to/project
# grep -rn '^class ' --include='*.py' . 2>/dev/null \
#   | grep -v '/archive/' | grep -v '/backend-archive-' \
#   | sed 's/.*:class //' | sed 's/(.*).*//' | sed 's/://' | tr -d ' ' | sort -u

# Class name aliases (workspace name differs from original)
ALT_MAP = {
    'MazdaChecksumCalculator': ['ChecksumCalculator'],
    'MazdaIDSSoftware': ['MazdaIDS'],
    'MazdaRaceEngineering': ['RaceEngineer'],
    'MazdaDiagnosticTest': ['DiagnosticTest'],
}

# Build source_file_classes dict from category+file analysis
def build_class_map(sources_dir):
    """Extract classes from all .py files in sources_dir."""
    import ast
    result = {}
    for f in sorted(os.listdir(sources_dir)):
        if not f.endswith('.py'):
            continue
        with open(os.path.join(sources_dir, f), errors='replace') as fh:
            try:
                tree = ast.parse(fh.read())
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                if classes:
                    result[f] = classes
            except SyntaxError:
                pass
    return result
