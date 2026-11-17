# Audit-Before-Implement Workflow

When implementing features from existing source files (legacy prototypes, reference
implementations, specification sources), always run a **pre-audit** before writing
any new code. Otherwise you risk re-implementing what already exists under a
different name.

## Pattern

```
Phase 0: Pre-Audit → Phase N: Implementation
```

### Phase 0 Steps

1. **List all source files** and extract every class name.
2. **Search the workspace** for each class name (exact + partial match).
3. **Check for functional equivalents** — e.g. `DPF_EGR_Manager` may already
   exist under that name inside a larger module even though no file is called
   `dpf_egr_manager.py`. Grep `^class .*DPF` to find it.
4. **Check for renamed equivalents** — sometimes `DiagnosticExploiter` became
   `AdvancedDiagnosticAccess`. Read the body, don't just match names.
5. **Diff against existing API routes** — Flask/PHP/Express routes may already
   have FastAPI equivalents.
6. **Output a confirmed-gap list** — only what's truly missing goes into the
   implementation plan.

### Pitfalls

- **Don't trust the file name.** A class called `MazdaSecurity` may live in
  `security_engine.py`, not `mazda_security.py`.
- **Don't trust `__init__.py` exports.** The class may exist but not be re-exported.
  Grep the entire workspace, not just imports.
- **Don't assume a single-file source maps to a single-file target.** The workspace
  may have already split sources into `app/protocols/`, `app/security/`, etc.
  Check the module structure.

## Protocol-Based Abstraction (testability)

When writing a module that depends on a class from a heavy import chain (e.g.
it needs `MazdaSecurity` from a module that triggers 5 other imports), define
a **Protocol** for the dependency instead of importing the concrete class:

```python
from typing import Protocol

class MemoryPatchBackend(Protocol):
    """Minimal interface for the dependency."""
    def memory_patch_runtime(self, address: int, data: bytes) -> bool:
        ...

class MyManager:
    def __init__(self, backend: MemoryPatchBackend) -> None: ...
```

Benefits:
- The module has **zero heavy imports** — testable anywhere.
- The concrete class is injected at runtime, not at import time.
- Tests use `MagicMock(spec=MemoryPatchBackend)` — no real hardware needed.

## Direct-Module Testing for Import-Heavy Codebases

When the target codebase has deep import chains (e.g. `app/__init__.py` that
pulls in every submodule including ones with missing native deps like `torch`),
standard `pytest` with `from app.muts.xxx import Yyy` will fail because the
package `__init__.py` fires first.

**Workaround:** Use `importlib` to load modules directly, bypassing the package
init chain. Combine with Protocol-based abstraction from the section above
for maximal decoupling:

```python
import importlib.util, sys, pathlib
from unittest.mock import MagicMock

def load_direct(module_name, file_path):
    spec = importlib.util.spec_from_file_location(
        module_name, file_path, submodule_search_locations=[])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load modules in dependency order
dc = load_direct('app.config.device_config', BASE / 'app/config/device_config.py')
hp = load_direct('app.config.hardware_profiles', BASE / 'app/config/hardware_profiles.py')

# Test with mocked Protocol dependency
backend = MagicMock(spec=dpf.MemoryPatchBackend)
manager = dpf.DPFEGRManager(backend)
```

**Requirements:**
- Modules must not have circular imports.
- Internal imports within each loaded module must use relative or fully-qualified
  paths that resolve in the `sys.modules` cache.
- Load in dependency order (leaf modules first).
