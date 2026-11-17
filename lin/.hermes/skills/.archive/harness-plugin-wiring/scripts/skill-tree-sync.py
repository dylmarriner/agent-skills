#!/usr/bin/env python3
"""Classify and sync a skill tree into a Hermes profile's skills dir.

Dry run (default) reports, per skill: missing / identical / differing.
--apply copies the missing ones. --force-differing also replaces the differing
ones, backing them up first (only after eyeballing the diff).

Why a filesystem walk instead of `hermes skills list`: that table has no
--json and truncates its name column, so grepping it yields false negatives.

Usage:
  skill-tree-sync.py SOURCE_ROOT [--dest ~/.hermes/skills] [--apply] [--force-differing]
  skill-tree-sync.py --self-test
"""
import argparse
import filecmp
import os
import shutil
import sys
import tempfile
import time


def find_skills(root):
    """Map relative skill dir -> abs path. Nesting depth varies; walk everything."""
    found = {}
    for dirpath, _dirs, files in os.walk(root):
        if "SKILL.md" in files:
            found[os.path.relpath(dirpath, root)] = dirpath
    return found


def frontmatter_ok(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    if not txt.startswith("---"):
        return False
    head = txt.split("---", 2)[1]
    return "name:" in head and "description:" in head


def classify(src_root, dest_root):
    missing, identical, differing = [], [], []
    for rel, spath in sorted(find_skills(src_root).items()):
        dskill = os.path.join(dest_root, rel, "SKILL.md")
        if not os.path.exists(dskill):
            missing.append(rel)
        elif filecmp.cmp(os.path.join(spath, "SKILL.md"), dskill, shallow=False):
            identical.append(rel)
        else:
            differing.append(rel)
    return missing, identical, differing


def sync(src_root, dest_root, apply_changes, force_differing):
    missing, identical, differing = classify(src_root, dest_root)
    src = find_skills(src_root)
    bad = [r for r, p in sorted(src.items())
           if not frontmatter_ok(os.path.join(p, "SKILL.md"))]
    print("source skills: %d | missing: %d | identical: %d | differing: %d"
          % (len(src), len(missing), len(identical), len(differing)))
    if missing:
        print("  missing:", ", ".join(missing))
    if differing:
        print("  differing (left alone unless --force-differing):", ", ".join(differing))
    if bad:
        print("  WARNING malformed frontmatter, loader will skip:", ", ".join(bad))
    if not apply_changes:
        print("dry run - pass --apply to copy the missing ones")
        return 0
    for rel in missing:
        dest = os.path.join(dest_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copytree(src[rel], dest)
    if force_differing and differing:
        backup = os.path.join(dest_root, ".skill-sync-backup-%d" % int(time.time()))
        for rel in differing:
            os.makedirs(os.path.join(backup, rel), exist_ok=True)
            shutil.copytree(os.path.join(dest_root, rel),
                            os.path.join(backup, rel), dirs_exist_ok=True)
            shutil.rmtree(os.path.join(dest_root, rel))
            shutil.copytree(src[rel], os.path.join(dest_root, rel))
        print("replaced %d differing copies, backup at %s" % (len(differing), backup))
    print("copied %d skills into %s" % (len(missing), dest_root))
    return 0


def self_test():
    def body(n):
        return "---\nname: %s\ndescription: d\n---\n" % n

    with tempfile.TemporaryDirectory() as tmp:
        src, dest = os.path.join(tmp, "src"), os.path.join(tmp, "dest")
        for rel, n in (("cat/a", "a"), ("b", "b"), ("cat/sub/c", "c")):
            os.makedirs(os.path.join(src, rel))
            open(os.path.join(src, rel, "SKILL.md"), "w").write(body(n))
        os.makedirs(os.path.join(dest, "cat/a"))          # identical
        open(os.path.join(dest, "cat/a", "SKILL.md"), "w").write(body("a"))
        os.makedirs(os.path.join(dest, "b"))              # differing
        open(os.path.join(dest, "b", "SKILL.md"), "w").write(body("OTHER"))
        missing, identical, differing = classify(src, dest)
        assert missing == ["cat/sub/c"], missing
        assert identical == ["cat/a"], identical
        assert differing == ["b"], differing
        sync(src, dest, True, False)
        m2, i2, d2 = classify(src, dest)
        assert m2 == [] and len(i2) == 2 and d2 == ["b"], (m2, i2, d2)
        sync(src, dest, True, True)
        assert classify(src, dest)[2] == [], "force-differing did not replace"
        print("self-test ok")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_root", nargs="?")
    ap.add_argument("--dest", default=os.path.expanduser("~/.hermes/skills"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-differing", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.source_root:
        ap.error("SOURCE_ROOT required (or --self-test)")
    return sync(a.source_root, os.path.expanduser(a.dest), a.apply, a.force_differing)


if __name__ == "__main__":
    sys.exit(main())
