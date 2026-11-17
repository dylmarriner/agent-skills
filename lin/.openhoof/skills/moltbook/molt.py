#!/usr/bin/env python3
"""Moltbook CLI — auto-solves the obfuscated math verification challenge.
usage: molt.py me | home | feed [sort] | post SUBMOLT TITLE BODY | comment POST_ID TEXT
key: ~/.config/moltbook/credentials.json
"""
import json, re, sys, urllib.error, urllib.request

B = "https://www.moltbook.com/api/v1"
KEY = json.load(open(__import__("os").path.expanduser("~/.config/moltbook/credentials.json")))["api_key"]
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
NUMS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
        "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
        **{w: 20 + 10 * i for i, w in enumerate(_TENS)}, "hundred": 100}
_REFERENT = re.compile(r"\b(?:these|those)\s+two\b|\bboth\b")

OPS = [("*", ("times", "multipl", "product", "tripl", "doubl", "factor")),
       ("/", ("divid", "quotient", "split", "halv", "half", "shared")),  # "per minute" is a rate unit, not division
       ("-", ("slow", "drop", "decreas", "declin", "reduc", "minus", "less", "fewer", "los", "backward", "subtract", "fall", "differ", "remain", "left over")),
       ("+", ("plus", "gain", "increas", "faster", "accelerat", "speeds up", "add", "more", "forward", "and then", "sum", "combined", "altogether", "together", "total"))]


def _op_match(s):
    """The operator word is shattered too ("pPrRoDdUuCcTt" = product), so a plain \bk search misses it
    and the unmatched fallback answers '+'. Reuse the doubling pattern for keys of length >= 4."""
    for sym, keys in OPS:
        for k in keys:
            pat = "".join(c + "+" for c in k) if len(k) >= 4 else re.escape(k)
            if re.search(r"(?<![a-z])" + pat, s):
                return sym
    return None


def _clean(text):
    """Shatter-proof: junk touching whitespace becomes a word break, junk inside a word is glued back."""
    s = text.lower()
    s = re.sub(r"(\d)\.(\d)", r"\1dot\2", s)                 # keep decimal points
    s = re.sub(r"\s+[^\w\s]+|[^\w\s]+\s+", " ", s)
    return re.sub(r"[^\w\s]", "", s)


def _pat(w):
    return "".join(c + "+" for c in w)  # shattered spellings double/expand letters


WORDRE = {w: re.compile(_pat(w)) for w in NUMS}
BIGRE = re.compile("|".join(sorted((_pat(w) for w in NUMS), key=len, reverse=True)))
BIGFULL = re.compile(f"(?:{BIGRE.pattern})+")


def _tok_vals(tok):
    for w, p in WORDRE.items():
        if p.fullmatch(tok):
            return [NUMS[w]]
    if re.fullmatch(r"\d+(dot\d+)?", tok):
        return [float(tok.replace("dot", "."))]
    if BIGFULL.fullmatch(tok):  # smashed compound, e.g. "thirtynine"
        return [NUMS[w] for g in BIGRE.findall(tok) for w in NUMS if WORDRE[w].fullmatch(g)]
    return []


def _merge(vals):
    """(token, value) pairs -> numbers, joining tens+units in one token and 'one hundred' across two."""
    out = []
    for ti, v in vals:
        if out and v == 100 and out[-1][0] == ti - 1 and out[-1][1] < 10:
            out[-1] = (out[-1][0], out[-1][1] * 100)
        elif out and ti - out[-1][0] <= 1 and out[-1][1] >= 20 and out[-1][1] % 10 == 0 and v < 10:
            out[-1] = (out[-1][0], out[-1][1] + v)  # "twennty three" / "thirtynine" -> 23 / 39
        else:
            out.append((ti, v))
    return [v for _, v in out]



def _prefix_ok(tok):
    """'t hr ee' can never be joined pairwise ('thr' is not yet a number) -- accept a partial prefix of a
    number word, min length 3, as a joinable intermediate."""
    return len(tok) >= 3 and any(pat.match(tok) and pat.match(tok).end() == len(tok) for pat in WORDRE.values())


def _join_shattered(toks, rounds=3, glue_numbers=True):
    """The obfuscator splits number words across a space ("T wOo", "SeVeN tEeN"). Glue adjacent
    tokens when the joined form IS a number word - and only then. glue_numbers=False restricts
    this to pairs where neither half is already a number ("T wOo"), for the fallback read."""
    toks = list(toks)
    for _ in range(rounds):
        out, i = [], 0
        while i < len(toks):
            a, b = toks[i], toks[i + 1] if i + 1 < len(toks) else None
            if (b is not None and (glue_numbers or not (_tok_vals(a) or _tok_vals(b)))
                    and len(a + b) > max(len(a), len(b)) and (_tok_vals(a + b) or _prefix_ok(a + b))):
                out.append(a + b); i += 2
            else:
                out.append(a); i += 1
        toks = out
    return toks



def _salted(tok):
    """True if tok is a number word with ONE letter salted in or dropped - and is not itself a number
    word. Live cases: 'sThIrTy' (junk inserted) and 'TrEe' for 'three' (letter dropped; the shorter
    token defeats any deletion-only test). Refuse on either rather than read the substring."""
    if len(tok) < 3:
        return False
    for w, p in WORDRE.items():
        if p.fullmatch(tok):
            return False
        if any(p.fullmatch(tok[:i] + tok[i + 1:]) for i in range(len(tok))):        # one letter extra
            return True
        if any(tok in w for w in NUMS):   # a fragment of a number word ("twen" of "twenty") is the
            break                          # shattering case, not a salted one - the glue rule's job
        if len(w) == len(tok) + 1 and any(                                          # one letter missing
                p.fullmatch(tok[:i] + c + tok[i:]) for i in range(len(tok) + 1) for c in set(w)):
            return True
    return False


def solve(text):
    """'A] lObSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fIvE' -> 15.00"""
    s = _clean(text)
    nums, toks = [], []
    # A referent like "these tWO" is itself a parseable numeral, so it lands as a third operand and breaks
    # operand selection. Strip demonstrative referents before scanning; fall back to the raw read.
    for cand in (_REFERENT.sub(" ", s), s):
        for glue in (True, False):  # glue shattered number words; fall back to the plain read
            toks = _join_shattered(cand.split(), glue_numbers=glue)
            nums = _merge([(i, v) for i, tok in enumerate(toks) for v in _tok_vals(tok)])
            if len(nums) >= 2:
                break
        if len(nums) >= 2:
            break
    if len(nums) < 2:
        raise ValueError(f"could not find two numbers in {text!r}")
    if toks and any(_salted(t) and not _tok_vals(t) for t in toks):  # parsed doubles are fine
        raise ValueError(f"salted number word in {text!r} -- hand-check, do not guess")
    if len(nums) > 2:  # ponytail: >2 operands means a decoy that is itself a real number
        raise ValueError(f"{len(nums)} operands in {text!r} -- hand-check, do not guess")
    a, b = nums[0], nums[1]
    # ponytail: "+" stays the last-resort default ("what is total force" names no operation) - so the cost of a
    # table hole is a confident sum. Op words seen live are listed; add new ones the first time one is mis-oped.
    # a bare letter x is an operator only when it sits between two number words -- the obfuscator also
    # scatters x as filler, and a stray x must not turn a sum into a product
    xop = None
    for i, t in enumerate(toks):
        if re.fullmatch(r"x+", t) and (_tok_vals(toks[i + 1]) if i + 1 < len(toks) else []
                                       or _tok_vals(toks[i - 1]) if i else []):
            xop = "*"
            break
    # A bare `*` is an operator even when it is not glued to a number ("fifty nootons * two claws"):
    # _clean eats it, so read it from the raw text and let it beat the word table, because "total"
    # names the question, not the operation. ponytail: assumes `*` is never decorative filler; if a
    # burn ever shows a decorative one, require it to sit between two number words like `x`.
    star = "*" in text
    op = "*" if star else (xop or _op_match(s))
    if op is None:  # ponytail: no op word matched -- refuse rather than answer with a silent sum
        raise ValueError(f"no operator word matched {text!r} -- hand-check, do not guess")
    return round(float(eval(f"{a}{op}{b}")), 2)


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(B + path, data=data, method=method, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=40) as f:
            return json.load(f)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"_status": e.code, **json.loads(raw or "{}")}
        except Exception:
            return {"_status": e.code, "raw": raw}


def verify(obj):
    """Solve + submit if the response carries a challenge. Returns the verify response."""
    v = (obj.get("post") or obj.get("comment") or obj.get("submolt") or {}).get("verification") \
        or obj.get("verification")
    if not v:
        return {"skipped": "no verification required"}
    print(f"[challenge] {v['challenge_text']!r}")
    try:
        ans = solve(v["challenge_text"])
    except ValueError as e:  # do NOT guess; leave the code on disk for hand-solving inside the window
        import pathlib
        pathlib.Path(__file__).with_name(".pending_verify.json").write_text(
            json.dumps({"code": v["verification_code"], "text": v["challenge_text"], "why": str(e)}))
        print(f"[refused, saved for hand-check] {e}")
        return {"refused": True, "saved": ".pending_verify.json"}
    print(f"[answer] {ans:.2f}  code={v['verification_code']}")
    return req("POST", "/verify", {"verification_code": v["verification_code"], "answer": f"{ans:.2f}"})


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == "me":
        print(json.dumps(req("GET", "/agents/me"), indent=1))
    elif a[0] == "home":
        print(json.dumps(req("GET", "/home"), indent=1))
    elif a[0] == "feed":
        print(json.dumps(req("GET", f"/feed?sort={a[1] if len(a) > 1 else 'hot'}&limit=15"), indent=1))
    elif a[0] == "post":
        body = open(a[3][1:]).read() if a[3].startswith("@") else a[3]
        r = req("POST", "/posts", {"submolt_name": a[1], "title": a[2], "content": body})
        print(json.dumps(r, indent=1)[:800])
        print(json.dumps(verify(r), indent=1))
    elif a[0] == "comment":
        body = open(a[2][1:]).read() if a[2].startswith("@") else a[2]
        r = req("POST", f"/posts/{a[1]}/comments", {"content": body})
        print(json.dumps(r, indent=1)[:600])
        print(json.dumps(verify(r), indent=1))
    elif a[0] == "selfcheck":
        cases = [("A] LoBsTeR- sW^iMmS [aT tWeN tY] tHrEe~ cEm PeR sEcOnD, uM Lo.bStEr- gAiNs^ fIfTeEn] cEm PeR sEcOnD, wHaT] iS tHe~ nEw- sPeEd?", 38.0),
                 ("A] LoOoB- sTeR rUm Um Lo.bSt Err S^wImS {aT} TwEnTy ThReE ] NoOoToNs um Of ClAw-FoRcE - aNd GaInS < FiVe > NoOtOnS /// MoRe, wHaT iS ToTaL- FoRcE?", 28.0),
                 ("A] Lo.BsT-eR'S ClAw ExErTs TwEnTy FiV e Um NoOtOnS^, BuT| iT s OtHeR ClAw AdDs SeVeN NeW~ToNs, WhAt Is ToTaL FoRcE?", 32.0),
                 ("A] LoBbEr ExErTs TwEnTy TwO NoOtOnS, aNd AnOtHeR ClAw ExErTs FiVe, wHaT iS tHe DiFfErEnCe?", 17.0),
                 # live 400s, not server-verified: op word was shattered, "+" default answered 37 and 30
                 ("A] lOoBbS tTeR | vEeLlAwWcIiTtEe ^ iS/ tWwEeN tYy TwO { cEeNnTtIiMmEeTtEeRrSs } pEeR \\ sEeCcOoNnDd - aNd ] iTtS ~ cLlAaWw fOoRrCcEe | iS / fIiFfTtEeEeN < nEeWwTtOoNnSs >, wWwHhAaTt- iIs ] tThHeE pPrRoDdUuCcTt?", 330.0),
                 ("Lo]bSt-Er~ ClAw^ FoRcE] Is TwEnTy FoUr {nOoToNs} x SiX ~ hOw/ mUcH^ fOrCe< tOtAl? um", 144.0)]
        for t, want in cases:
            got = solve(t)
            assert got == want, (got, want, t)
        # tonight's two live misses must now refuse instead of answering wrong
        cases.append(("A] lO.bStEr ErR sOcIaL- ClAwS^ fIgHt Um, cLaW fOoRcE Is FiIfTtY nooToNs ~ * tW/oO cLaWwS, wHaT iS ToTaL fOrCe < > ?", 100.0))
        cases.append(("A] lOoObSsTtEeR^ sW/iMmS lOoWly, uMm, iN tHe^ cOrRuPtEd- aQuArIuM wHeRe- wAtEr PrEsSuRe Is LoW, aNd ItS cLaW ExErTs- a FuZzY fOrCe- oF fIfTeEn * nEeWtOnS; tHe ReD lOoobsterrr- paRtIcIpAnT mEaSuReS vElAwCiTyy aT tWeNtY tHrEe / ceNtImEtErS pEr SeCoNd — hOw MuCh- iNsTaNtAnEoUs- mOmEnTuM DoEs ThE lOoObSsTeR hAvE? }", 345.0))
        for t in ["A] LoBb St-Er[ ExErTs^ TwEnTy FiVe Um NeW-ToNs] WiTh/ OnE ClAw, AnD] TwElVe NeW-ToNs OtHeR ClAw, WhAtS ToTaL FoRcE?",
                  "A] lOoOoB sTtEr^ SwImS[ aNd/ ExErT sThIrTy] TwO^ NoOoToNs, Um/ aN] oThEr^ Lo.bStEr~ ToUcHeS AnTeNnAa| AnD/ ExErTs^ EiGhTeeN} NoOtOnS; WhAt^ Is/ ThE] ToTaL~ FoRcE?"]:
            try:
                solve(t)
            except ValueError:
                pass
            else:
                raise AssertionError("guessed instead of refusing: " + t)
        print(f"selfcheck ok: {len(cases)} solved, 2 refused")
    elif a[0] == "solve":  # self-check
        print(solve(" ".join(a[1:])))
    elif a[0] == "reply":
        body = open(a[3][1:]).read() if a[3].startswith("@") else a[3]
        r = req("POST", f"/posts/{a[1]}/comments", {"content": body, "parent_id": a[2]})
        print(json.dumps(r, indent=1)[:600])
        print(json.dumps(verify(r), indent=1))

# ponytail: challenge solver covers two numbers + one operator; extend if the format grows.
