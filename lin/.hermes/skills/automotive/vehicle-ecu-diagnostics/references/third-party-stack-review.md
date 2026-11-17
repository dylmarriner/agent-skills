# Reviewing an outside diagnostic stack (repo, vendor tool, another agent)

## When to use

A bare repo URL, a vendor tool, a firmware dump, or someone else's diagnostic agent lands in the
session with no explicit question. The implicit ask is a verdict: what is this, does it reach the
bus, and is any of it worth taking. Answer that; do not install it, do not port it, and do not run
it against a vehicle.

## Read order

Read in this order, because each stage invalidates the previous one:

0. **A page URL is not a repo.** For an article, vendor guide or docs site, read the *rendered*
   text rather than settling for a summary-level extraction: `browser_exec` with
   `js('document.body.innerText')` returns the whole page (a long vendor guide lands around 25–35 kB)
   and can be paged through in slices. Read the linked companion page the article keeps recommending
   too — the actionable method is often there, not in the page that was handed to you.
1. **Shallow clone into scratch, never into the project.**
   `git clone -q --depth 1 URL ~/.hermes/cache/scratch/<name>` then `find <name> -type f -not -path '*/.git/*'`
   and `find <name> -name '*.py' | xargs wc -l`. Size and file count settle the "is this a demo"
   question before any line is read.
2. **Look for the companion repo.** Agent-side demos usually ship a device/firmware repo. The
   firmware is where the tool surface and any boundary actually live, so a review that stops at the
   Python side has not seen the interesting code. Its README header usually names it.
3. **Transport first.** What does it actually speak? `grep -rn "import obd\|python-obd\|serial\|ISO15765\|AT ".`
   An ELM327 AT-command string bridge is OBD-II Mode 01/03/09 only: no module addressing, no ISO-TP
   framing, no UDS DIDs. Say that in one line and stop comparing feature lists.
4. **Tool surface second.** `grep -n '.name =\|\.handler =\|input_schema_json\|tools\[\]\|def send_'`.
   List every tool the agent can call and, for each, what its argument reaches.
5. **Prompt last.** The system prompt is the project's real policy. Read it in full and note every
   command it instructs the model to send.

## The write-primitive audit

A tool whose argument is a free-text command handed to the adapter's send function has no boundary.
The check is mechanical: find the tool handler, follow the argument, and see whether anything filters
it before the driver call.

```c
// mcp_tools.c — the whole handler
command = cJSON_GetObjectItem(args, "command")->valuestring;
ret = elm327_send_command(command, response, sizeof(response), ELM327_DEFAULT_TIMEOUT);
```

Three lines, zero filtering, and the model has a raw write primitive. Now cross-check the prompt: if
it *tells* the model to send a write service (clear-DTC `04`, `2E`, a routine `31`, an `AT`
programming command), then the allowlist is one sentence of prose that a prompt-injection or a
re-entered turn can walk straight past. Prompts are not guards; report the pairing as the finding.

This is the strongest available argument for keeping the guard in code: an external stack that
'trains' its model to write is a live demonstration of why an allowlist has to sit where the frame
is built.

## Verdict shape

Lead with what it is and what it speaks, then a table of parts against reality:

| Part | Reality |
|---|---|
| Transport | what protocol, real module addressing or not |
| Decode/helper layer | small and usable, or a re-implementation of what the repo already has |
| Prompt / agent layer | what it hands the model |
| UI / presentation | anything genuinely reusable |
| Firmware / device side | what it exposes, and to whom |

Then exactly two lists: **the one or two things worth taking** (name the file and line), and **the
thing to refuse**. Refuse by default: a second transport or decode implementation next to a working
one, and anything whose only boundary is prompt text. Take small, non-toy pieces — a structured
payload block a UI parses out of a chat stream, a device-side server that removes a bridge from the
path.

Close with the clone paths and offer to move them into the project's `archive/`; scratch prunes them.

## Pitfalls

- **Do not bench the thing against the car to 'see if it works'.** A demo that exposes a raw command
  string is exactly the tool that will fire a write service by accident. Judge it by reading.
- **A simulator is a UI/dev target, never a substitute for the bus.** A fake ELM327 with injected
  DTCs answers everything and proves nothing about framing, addressing or timing.
- **Star count and README architecture diagrams are not evidence.** The `tools.py`/`prompts.py`/
  handler source is; hackathon scoring text is not.
- **Do not re-derive decode math that the project already has.** Recognising a clean helper is not a
  reason to adopt it when an equivalent one is already in the repo's collector.
