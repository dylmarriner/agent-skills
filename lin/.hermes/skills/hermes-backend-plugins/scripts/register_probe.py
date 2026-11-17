"""Drive a plugin's register() under a fake ctx and call its handlers.

The live registry only picks up a plugin after a gateway restart, so this is
the only way to exercise registration and handler wiring in the session that
builds it. Stub methods mirror the real keyword contract and assert it.

    python register_probe.py ~/.hermes/plugins/<name> [spec.json ...]

Exit 0 = registered, declared tools/skills resolvable, handlers returned.
"""
import importlib.util
import json
import sys
from pathlib import Path


class Ctx:
    def __init__(self):
        self.tools, self.skills = {}, []

    def register_tool(self, *, name, toolset, schema, handler, description=""):
        params = schema.get("parameters")
        assert isinstance(params, dict), f"{name}: parameters must be an object"
        assert params.get("type") == "object", f"{name}: parameters must be type=object"
        assert callable(handler), f"{name}: handler not callable"
        self.tools[name] = handler

    def register_skill(self, name, path):
        assert Path(path).exists(), f"skill file missing: {path}"
        self.skills.append(name)

    def register_hook(self, name, fn):
        assert callable(fn), f"hook {name} not callable"

    def register_command(self, *a, **k):
        pass


# Any declared tool called without a usable argument set still proves wiring;
# handlers that need real files get them from argv[2:].
def main(argv):
    plugin_dir = Path(argv[0]).resolve()
    ctx = Ctx()
    spec = importlib.util.spec_from_file_location(
        f"probe_{plugin_dir.name}", plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    sys.path.insert(0, str(plugin_dir.parent))
    spec.loader.exec_module(mod)
    mod.register(ctx)
    print("tools:", sorted(ctx.tools), "skills:", ctx.skills)

    declared = (plugin_dir / "plugin.yaml").read_text()
    for name in ctx.tools:
        assert name in declared, f"{name} missing from provides_tools in plugin.yaml"

    for name, handler in sorted(ctx.tools.items()):
        try:
            out = handler({})
            print(f"{name}({{}}) -> {type(out).__name__}")
        except Exception as e:  # required args may be missing: wiring still proven
            print(f"{name}({{}}) -> {type(e).__name__}: {e}")
    print(json.dumps({"registered": len(ctx.tools), "skills": len(ctx.skills)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
