#!/usr/bin/env bash
# scan_git_repos.sh
# Discover all git repos under ROOTS, report remote/branch/ahead-behind/dirty.
# With --repoint OWNER, rewrite origin to https://github.com/OWNER/<same-name>.git
# (URL-only; NEVER pushes — push manually per SKILL.md §3/§4).
# With no args, scans default roots.
set -u

REPOINT=0; NEWOWNER=""
if [ "${1:-}" = "--repoint" ]; then
  REPOINT=1; NEWOWNER="${2:-}"; shift 2
fi

if [ "$#" -gt 0 ]; then
  ROOTS=("$@")
else
  ROOTS=("$HOME/Documents" "$HOME/CascadeProjects" "/mnt/development1")
fi

echo "Scanning roots: ${ROOTS[*]}"
echo "----------------------------------------------------------------------"

while IFS= read -r gdir; do
  repo="${gdir%.git}"
  url=$(git -C "$repo" remote get-url origin 2>/dev/null || echo "")
  branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  upstream=$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "none")
  if [ "$upstream" = "none" ]; then
    ahead="NO-UPSTREAM"; behind=""
  else
    read behind ahead < <(git -C "$repo" rev-list --left-right --count "$upstream"...HEAD 2>/dev/null || echo "0 0")
  fi
  dirty=$(git -C "$repo" status --porcelain 2>/dev/null | head -3)
  [ -z "$dirty" ] && dirty="clean"

  printf 'REPO=%s\n  url=%s\n  branch=%s upstream=%s ahead=%s behind=%s\n  dirty=%s\n' \
    "$repo" "$url" "$branch" "$upstream" "$ahead" "$behind" "$dirty"

  if [ "$REPOINT" = "1" ] && [ -n "$url" ]; then
    base=$(basename "$repo")
    newurl="https://github.com/$NEWOWNER/${base}.git"
    if [[ "$url" != *"$NEWOWNER/"* ]]; then
      git -C "$repo" remote set-url origin "$newurl"
      echo "  >> repointed -> $newurl"
    else
      echo "  >> already under $NEWOWNER, skipping"
    fi
  fi
  echo "----------------------------------------------------------------------"
done < <(find "${ROOTS[@]}" -type d -name .git 2>/dev/null | sort)
