---
name: hermes-backend-plugins
description: Build Python plugins that add tools and skills.
version: 1.0.0
platforms: [linux, macos]
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, plugins, tools, validation]
    category: productivity
    related_skills: [hermes-desktop-plugins, hermes-plugin-development]
---

# Hermes Backend Plugins

Python plugins in `~/.hermes/plugins/<name>/` that add model-visible tools and
bundled skills. Sibling of `hermes-desktop-plugins` (that one is the app's JS UI
plugins — different API, different directory).

For hook points, transform patterns, and integration case studies see the
archived depth skill: `skill_view('.archive/hermes-plugin-development')`.

## When to Use

- The user asks for a new capability that should be a tool or an auto-loading
  skill rather than a one-off script.
- An existing workflow needs to reach the model as first-class tools with
  validated arguments.
- Not for UI panes and commands — that is `hermes-desktop-plugins`. Not for
  editing an already-installed plugin's behaviour in place: patch its source,
  then re-run the verification block.

## Contract — read the source, never guess it

The API authority is `hermes_cli/plugins_context.py::register_tool` plus any
installed plugin that ships tools. Open a real one before writing `register()`:
`~/.hermes/plugins/agent-fix-lab/__init__.py` (full form) and
`~/.hermes/plugins/hermes-plugin-guard/tests/fixtures/safe_plugin/__init__.py`
(minimal form). Both shapes below were wrong on the first guess once.

```python
def register(ctx):
    for name, (desc, props, required) in SCHEMAS.items():
        def handler(args, _name=name, **kwargs):
            return dispatch(_name, args)
        ctx.register_tool(
            name=name,
            toolset="my-plugin",
            schema={"description": desc,
                    "parameters": {"type": "object", "properties": props, "required": required}},
            handler=handler,
            description=desc,
        )
    ctx.register_skill("my-skill", Path(__file__).parent / "skills/my-skill/SKILL.md")
```

- Schema is ONE dict: `{"description": str, "parameters": <object schema>}`. A
  non-dict `parameters` raises at registration; the `properties`/`required`
  keys are what the model actually fills.
- The handler is called `handler(args, **kwargs)` — `args` is the validated
  argument dict. `def handler(**kwargs)` silently gets nothing useful.
- Handlers return JSON-serialisable data; async only with `is_async=True`.
- `plugin.yaml` must list every tool in `provides_tools` and every hook in
  `provides_hooks`, plus `manifest_version: 1` and `api_version: 1`.
- Plugin-provided skills are namespaced `<plugin>:<skill>` and are NOT
  reachable by bare name from `skill_view`.

## Procedure

1. `mkdir -p ~/.hermes/plugins/<name>/skills` — hyphens are fine in the dir name.
2. Write `plugin.yaml` (name, version, manifest_version, api_version,
   description, license, tags, provides_tools, python_dependencies).
3. Write `__init__.py` with `register(ctx)` per the contract above; keep the
   logic in a sibling module so `python <module>.py demo` can test it without
   Hermes.
4. Give every non-trivial path ONE runnable check — a `demo()` with asserts or
   a `test_*.py`. No frameworks.
5. Validate, probe, doctor, enable (see Verification).
6. Tell the user to restart the gateway from an outside shell.

## Dependencies

Declare third-party packages in `python_dependencies`; `hermes plugins enable`
installs them. Every entry needs an upper bound, and the band must fit what
core already pins — `hermes plugins enable` resolves with `uv lock`, so a bound
that excludes a core pin aborts the enable with `DependencyConflict`. Read the
extras in the Hermes `pyproject.toml` (`documents`, `documents-pdf`, …) and pin
inside them, e.g. `reportlab>=5.1,<5.2` against core's `reportlab==5.1.0`.

Never rely on `pip` inside the Hermes venv — frequently absent. Discover the
venv (`ls ~/.hermes/installs/*/environments/*/venv/bin/python`) and use
`uv pip install --python <venv>/bin/python <pkg>` for ad-hoc needs.

## Verification, in this order

```bash
cd ~/.hermes/plugins/<name>
hermes plugins validate .            # path, not name: catches load, drift, collisions, security
python scripts/register_probe.py .   # register() under a fake ctx + call the handlers
hermes plugins doctor <name>         # dependency + runtime contracts
hermes plugins enable <name> && hermes plugins show <name>
```

`register_probe.py` lives in this skill's `scripts/` and also checks that every
registered tool is declared in `provides_tools`. Then run the real
artefact and look at it (screenshot + `vision_analyze`); a passing
registration says nothing about output. Traps in the renderer itself:
`references/docx-pdf-rendering.md`.

## Scope — grow the plugin, not the plugin count

One plugin per domain. A related capability that consumes or produces the same
artefacts becomes another tool in the existing plugin (and another skill), not a
sibling package: the model then sees one coherent toolset, and the shared pins,
validation and the single `demo()` keep working. A new plugin is for a new
domain.

Every added tool costs a `provides_tools` entry plus its schema in the same
commit; `hermes plugins validate .` fails on the mismatch, which is the guard.

## Pitfalls

- `hermes plugins validate docforge` fails with `is not a directory` — pass `.`
  from inside the plugin dir.
- `hermes gateway restart` refuses from inside a Hermes `terminal` call
  (SIGTERM would kill the command). Tools and newly enabled dependencies only
  load in a process started after the enable; the session that built the
  plugin never sees its own tools.
- `hermes plugins enable` warns `dependency … installed after the gateway
  started` — that is the restart requirement, not an error to work around.
- A stub `ctx` that only implements `register_tool(name, fn, schema)` will
  swallow the real keyword contract. Assert `schema["parameters"]["type"]`
  inside the stub so a malformed schema fails the probe.
- Keep all handler logic out of `__init__.py` and import it lazily; a plugin
  hook that raises is treated as deny and blocks every later tool call.
- Do not shadow built-in tool names without `override=True` and the operator
  opt-in `plugins.entries.<id>.allow_tool_override: true`.
- `hermes plugins validate .` runs an isolation probe and can pass the default
  180s terminal timeout. Give it 400s+ or it reads as a hang.
- After a Hermes source update the environment path recorded earlier can vanish.
  Re-discover the venv (`ls -dt ~/.hermes/installs/*/environments/*/`) and prove
  the deps import (`python -c "import docx, reportlab"`) before reusing a path.
- Success flags: an advisory note ("auto-picked candidate", "fallback used") must
  not flip `ok` to false. Prefix notes and exclude them when computing the flag,
  or every automatic run reports failure and callers learn to ignore it.
- Assert the invariant, not the artefact of your implementation. A precision
  assert against a hard ground-truth mask fails legitimately once deliberate
  antialiasing exists — measure cores (alpha >128) for precision, any alpha for
  recall.
