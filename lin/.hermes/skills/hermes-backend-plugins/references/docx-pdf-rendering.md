# Rendering DOCX/PDF in a plugin: the traps that pass tests

A plugin whose output is a document can pass every registration check and still
ship a broken artefact. Render one, convert, look at it. Traps below cost a
rewrite each.

## Numbers to words

`"  twenty thirty forty".split()` gives `['twenty', 'thirty', 'forty']` — the
leading spaces vanish, so `_TENS[n // 10]` is off by two and 21 becomes "forty
one". Use an explicit 0-indexed list with two blanks:

```python
_TENS = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
```

Assert `in_words(21) == "twenty one"` and a four-digit case in the demo; an
off-by-one here is invisible until someone reads the document.

## ReportLab flowables

- `HRFlowable` renders at the *bottom* of its own space, so a rule pushed
  before a heading lands underneath it and strikes through the next line. Push
  the rule **after** the block it should follow, with `Spacer` on both sides.
- Flowable lists are `list[Flowable]`: appending a `Table`/`Image`/`Spacer` to a
  list typed `list[Paragraph]` type-checks wrong but runs. Annotate as
  `list[Flowable]` if pyright is in the loop.
- `Paragraph` text is XML-ish: `&` must be `&amp;` — invoice footers contain it.

## python-docx

- `doc.add_paragraph()` with no text has `runs == []`; call `.add_run(...)` on
  the returned paragraph instead of indexing `paragraph.runs[0]`.
- `add_paragraph("x").runs[0].bold = True` is fine — that run exists.
- Bytes, not a path: `doc.save("out.docx")` accepts both, but saving to a
  `Path` of an uncreated directory silently fails — `mkdir(parents=True)` first.
- Tables: set `style = "Table Grid"` or borders vanish in every consumer but
  Word's own preview.

## Verification without a GUI review loop

```bash
soffice --headless --convert-to pdf out.docx --outdir /tmp/chk   # docx -> pdf
pdftoppm -r 90 -png -f 1 -l 1 out.pdf /tmp/chk/p                  # pdf -> png
```

Then `vision_analyze` the PNG and ask specifically whether anything overlaps
or is misaligned. Ask about a *region* for fine detail; ask "any overlap"
plainly rather than "does it look fine".
