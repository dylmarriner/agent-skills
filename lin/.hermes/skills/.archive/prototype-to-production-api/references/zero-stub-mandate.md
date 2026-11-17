# Zero-Stub Mandate — All Languages, All Contexts

## Core Rule

Every function you write must be a real working implementation that does real work
or fails meaningfully. This applies to ALL languages: Python, Rust, C, Java,
Objective-C, Swift, JavaScript, Go — no exceptions.

## What is NOT Production Code

| Pattern | Example | Why It Fails |
|---------|---------|--------------|
| Mock return values | `return "MSC001"`, `return {"status": "compromised"}` | Hardcoded data pretending to be a real result |
| Simulated progress | `print("[+] Patching...")` + `time.sleep(3)` + `print("[+] Done")` | No actual work done — just theater |
| Stub struct fields | `msc: Some("MSC001".into()), vlr: Some("VLR001".into())` | Fake identifiers in a real data structure |
| Simulated states | `state: Some("assumedIdle".into())` | Synthetic state pretending to be parsed from real data |
| Empty struct constructors | `Default::default()` on structs with no real data | Carries no information, wastes allocation |
| Placeholder strings | `return "not yet implemented"` | Useless to the caller |
| `pass` function bodies | `fn do_thing() { }` (empty) | Doesn't do what the name says |
| `NotImplementedError` | `raise NotImplementedError` | Abandons the caller |
| `TODO` / `FIXME` comments | `// TODO: implement this later` | Committed debt |
| Print-based "progress" | `println!("Step 1 done")` with no actual operation | Logging isn't execution |
| Simplified demo code | `// simplified for demo` | Code that doesn't handle real cases |
| Dead Default import | `use std::default::Default` on struct with all manual fields | Import has no callers |

## What IS Acceptable

- A function that connects to a real resource and returns `Err`/`Result::Err` when
  the resource is unavailable. The caller gets a real error, not fake data.
- A function that parses real input and returns an error for invalid formats.
- `return None` or `return null` for "not found" — this is a meaningful result.
- `return true/false` for success/failure of an operation.

## Language-Specific Notes

### Rust
- No `todo!()` or `unreachable!()` outside match arms that are truly unreachable
- No `Default::default()` on structs where most fields will be garbage
- No fake struct fields — `msc: Some("MSC001")` is just data theater. Either
  parse real data or return `None`.
- No simulated state strings like `assumedIdle`, `simulatedConnected` — these
  are indistinguishable from mock data.
- `Result::Err` with a descriptive error string is PRODUCTION CODE — it correctly
  communicates failure
- `Option::None` is production code — it correctly communicates absence
- Remove unused imports (`use std::default::Default` with no callers)

### Python
- No `raise NotImplementedError` — ever
- No `pass` as a function body
- No `return "stub response"` strings
- No `time.sleep(n)` simulating work
- `return None` for not-found is acceptable
- `return True/False` for delete/update status is acceptable

### Java / Objective-C
- No empty method bodies
- No `// TODO` comments
- No returning null where a real object is expected
- Catch blocks must handle the error, not be empty

## When to Fail vs. When to Mock

**Fail meaningfully**: When the function's success depends on an external resource
(network, USB device, file system), try to connect and return a real error on
failure. The caller deserves to know WHY something failed.

**Do NOT fake success**: Returning `Ok(MSC001)` when no SS7 gateway was contacted
is worse than returning `Err("No M3UA gateway configured")`. The latter is honest.

**Testing**: Mocking is for TESTS, not for production code paths. If you're writing
a test, use a mock. If you're writing the actual function, use real implementation.

## Verification Checklist

Before delivering any code:
- [ ] Every function does real work or returns a real error
- [ ] No hardcoded return values pretending to be computation results
- [ ] No fake struct fields (stub identifiers, simulated states)
- [ ] No `sleep()` simulating operations
- [ ] No `TODO`, `FIXME`, `stub`, `placeholder`, `simplified` markers
- [ ] No unused imports left behind after edits
- [ ] `Err`/`None` outcomes are documented in function docs
- [ ] The function would actually produce correct results if given real inputs/resources
