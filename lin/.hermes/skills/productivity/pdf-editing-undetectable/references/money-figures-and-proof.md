# Money, figures, and proving the edit

Depth for two things that bite on invoiced documents: repricing charges so the
bookkeeping survives an audit, and proving a multi-row edit ran clean. Pairs with
the table-driven script shape in SKILL.md.

## Repricing

A date change does nothing to amounts. "Adjust the pricing to suit the new months"
means: reprice what is period-dependent, leave what is not.

- **Leave the plan/one-off charge alone.** A plan price does not move month to
  month; moving it makes the document disagree with the one before it.
- **Pick one arithmetic rule the user can audit** and apply it everywhere: the
  month's day count (31/30 on a fee), a rate change, a credit. Derive every
  dependent figure from it — line item, subtotal, section total, GST line, grand
  total — rather than choosing them individually.
- **GST is inclusive on NZ documents** at 15/115 of the GST-inclusive amount. A
  total's GST equals the sum of its parts' GST, so both must move together or the
  invoice contradicts itself.
- Repricing an amount means redacting the widest of old and new ink and
  right-aligning to the original right edge, exactly like any other value.

## Self-check before saving

Read the finished document back and assert the relationships:

```python
assert abs(total - (opening + fee)) < 0.005
assert abs(gst - round(fee * 15 / 115, 2)) < 0.005
```

A failing figure then fails the run instead of shipping. Print the reconciled
numbers on success so the log carries them.

**Amounts are their own text block, so `" ".join(spans)` per line gives you a label
with no value.** Pair by baseline: collect every `$`-prefixed line, and for each
label line take the money line whose `bbox[3]` is within 2 pt. A label carrying its
amount inline (`GST amount of $2.33`) needs its own `\$(\d+\.\d\d)` grab from the
line text, which always wins over the baseline lookup.

## Proving the chain

1. `cp` the file to a scratch copy, point `SRC` at it, and rebuild the whole
document **from the pristine `.bak` in one pass**. Read the log: every row fires,
in order, and no row depends on an earlier one having run. Incremental re-runs hide
ordering bugs — a row that only matches because the previous pass left the text in
that state — and hide rows the in-place file already consumed.
2. Re-run on the result: every row prints `skip ... already applied`, then
`nothing to do`.
3. Per-page render diff against `.bak` at 2x: changed pixels confined to the target
spans, untouched pages bit-identical.
4. Full-page and per-region crops read with `vision_analyze` — digits matching the
neighbouring face and weight, right edge flush, no ghosts, no overlap.
