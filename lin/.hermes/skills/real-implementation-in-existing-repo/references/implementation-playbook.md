# Implementation playbook

Depth for the real-implementation workflow: classify what you found, promote what is
already there, scaffold the test that pins it.

## Classify before you write

| What you found | How to tell | What to do |
|---|---|---|
| Pure stub | a few hundred bytes, body is a header comment or `pass` | implement from the spec; the file name is the interface |
| Refusal-only shell | every entry point `raise`s, but metadata/enums/tables are real | keep the structure, wire the real path, keep only legitimate refusals |
| Thin facade | the real work lives in a sibling module; this one forwards | delegate; do not re-implement the sibling |
| Dead code after `raise` | a working body sits unreachable below an early refusal | promote it above the `raise`; the author's constants live there |
| Partial protocol layer | docstring says "only the standard framing; the rest comes from the caller" | the gap is domain values, not transport: add a spec/constants module and let the caller supply what is unpublished |
| Silent failure | catches everything and returns `[]`/`None`/`{"error": ...}` | highest priority: it pretends to work |

A refusal that exists because an input is genuinely unknown is **not** a stub. Check
whether the input is knowable before "fixing" it.

## Promote dead code, don't rewrite it

```python
# before: the body below the raise is unreachable but is the author's real work
def calculate_key(self, seed: bytes, level: int) -> bytes:
    raise AlgorithmUnavailable("no verified algorithm")
    key = bytearray(4)
    for i in range(4):          # keep these constants: recoverable nowhere else
        temp = seed[i] ^ 0x73
        ...

# after: same body, reachable, behind a named provider the caller can substitute
def calculate_key(self, seed, level, context=None):
    provider = self.providers.get(self.profile.provider_name(level))
    return provider.calculate(seed, level, context)
```

Delete nothing below the `raise` until the promoted version passes a test pinning the
known-good output.

## Provider + typed refusal (the reusable shape)

Use whenever a step depends on a secret, key, vendor routine or device profile the code
cannot know by itself:

```python
@dataclass(frozen=True)
class Provider:
    name: str
    inputs: Tuple[str, ...]          # what it needs, by name
    derive: Callable[..., bytes]

    def calculate(self, *args, context: Optional[Mapping[str, object]] = None) -> bytes:
        missing = [k for k in self.inputs if (context or {}).get(k) is None]
        if missing:
            raise ProviderMissingError(
                f"{self.name} needs {', '.join(missing)} in the context"
            )
        return self.derive(*args, context or {})
```

Rules that keep it real rather than decorative:

- The registry is populated at construction, so a provider an operator adds is picked up
  without code changes; the profile maps a request to a provider **by name**.
- Resolve the provider and raise a named error **before** opening the transport.
- Refusals are typed and specific, never a bare `False` or a silently empty result.
- Unknown target (level, module, device) is refused by name, including how to register it.

## Test scaffolding that pins behaviour

Scripted fakes plus injected time. No fixtures, no extra frameworks.

```python
class ScriptedTransport:
    """Answers from a table; records everything it was asked."""
    def __init__(self, answers):
        self.answers, self.requests = answers, []
    def request(self, payload):
        self.requests.append(bytes(payload))
        return self.answers[bytes(payload)]

def make_service(**kw):
    now, slept = {"t": 0.0}, []
    return Service(
        ScriptedTransport({b"\x27\x01": b"\x67\x01\x11\x22\x33\x44"}),
        clock=lambda: now["t"],
        sleeper=lambda s: (slept.append(s), now.__setitem__("t", now["t"] + s)),
        **kw,
    )
```

Assertions worth making, one per real bug class:

- **nothing was sent**: `assert transport.requests == []` on the refusal path — proves the
  fail-before-side-effect rule, not merely that something raised
- **the exact bytes asked for**: compare against the raw request, not a mock's echo
- **state after failure**: counter incremented, pending state cleared, delay window armed
- **the window is honoured**: `wait_for_delay` returns the expected elapsed time and the
  keep-alive traffic went out — with injected clock/sleeper, without real sleeping
- **duplicate/replay rejection**: the same input twice must not be accepted twice

## Prove a test failure is not yours

```bash
pytest tests/touched_a.py tests/touched_b.py -q              # your work: expect green
mv your_new_pkg /tmp/hidden && pytest tests/neighbour*.py -q  # identical failures ⇒ pre-existing
mv /tmp/hidden your_new_pkg
```

Also check `git status --porcelain <failing module>`: a file already dirty in someone
else's working tree, which does not reference your new packages, cannot be your
regression. Report it per file — never present a mixed suite as green.
