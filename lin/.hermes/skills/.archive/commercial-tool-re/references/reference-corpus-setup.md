# Building a Reference Corpus for an RE Programme

Before reversing anything, gather every public implementation of the same problem and index it. Ten minutes of cloning beats a week of guessing, and the corpus is what makes a finding checkable later.

## Layout

Clone into one directory that the host project ignores — `<project>/reference/` — never loose in the repo root:

```bash
grep -q '^/reference/$' .gitignore || printf '\n# Third-party reference clones\n/reference/\n' >> .gitignore
git check-ignore -v reference   # prove it, do not assume
```

## The clone script

Make it re-runnable and self-reporting: skip existing clones, delete half-written ones so the next run retries, and print `name HEAD purpose` per line. One `xargs -P4` over a `slug:why-it-is-here` list is enough; keep the "why" beside the slug so the index stays honest after the fact.

**Probe every slug before a batch clone runs.** Projects get renamed and moved, and a dead slug aborts that entry mid-batch:

```bash
for u in owner/name owner/renamed owner/other; do
  printf '%-28s ' "$u"
  timeout 15 git ls-remote --exit-code -h "https://github.com/$u.git" >/dev/null 2>&1 && echo EXISTS || echo no
done
```

That check caught a repository that had moved (`udsoncan` -> `python-udsoncan`) and a project whose public repo is a README-only redirect telling you the real tree is kept private. In the second case clone the piece that *is* published (the loader, the CLI, the library) and note in the script comment why the firmware/main artefact is absent, rather than shipping a one-file clone that looks like a failure.

If a project advertises itself as open source but no repository is public (site, no git remote), record it as unavailable and move on — never invent a URL.

## Generate the index, do not hand-write it

Walk the clones and emit `reference/INDEX.md`: project, HEAD commit, licence file present, size, remote. Real HEADs from disk beat a list typed from memory; the HEAD is also what makes a later finding reproducible.

## Extract facts, keep them out of context

A corpus is unreadable in bulk. Write a script that classifies matches into the vocabulary the work needs — data identifiers, bus addresses, service ids, security-access terms, ROM layout, checksums, flash sequencing, map/table terms — and emits:

- `docs/<area>/<corpus>_facts.json` — every match, machine readable
- `docs/<area>/<CORPUS>_FACTS.md` — grouped by category, each row `file:line` + the literal text

Cap hits per category per repository so one verbose project does not drown the rest, and print only counts plus a few rows to the terminal. Every stored fact must keep its `file:line` pointer so it can be re-checked; an extracted fact without a pointer is an assumption.

## Record the negative findings too

What the public corpus does **not** contain is the most valuable early output, because it defines the work. When the reference tool imports the hard part from a private package (a `_secure.py` present only as a stub that raises `ModuleNotFound`, an SBL/seed-key helper provided by the vendor) that is a hard finding: the algorithm has to come out of the target itself. Write it down with the `file:line` of the stub and what it proves, alongside the positive findings.

Same for platforms the corpus never supported — a "planned support" line in a README tells you where the untouched ground is.

## Then write the plan, not the code

Close the corpus step with a programme document: workstreams, each with the known facts (with pointers), what is missing, the method and tool, and where the output lands in the host project. Put the blocking gate first — usually "obtain the artefact" (a firmware image, a bus capture, a licence) — so the plan cannot be started from the wrong end. Evidence rules belong in the same document: a finding needs the command that produced it plus a hash of the artefact, and no algorithm ships until it reproduces a real observed pair.
