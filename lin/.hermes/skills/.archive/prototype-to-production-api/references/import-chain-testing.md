# Testing Modules with Deep Import Chains

When a package `__init__.py` pulls in heavy dependencies (torch, docker, aiohttp, etc.),
importing any submodule triggers the entire chain and fails with `ModuleNotFoundError`.

## Solution: Direct Module Loading with importlib

Bypass the package `__init__.py` by loading modules directly from their file paths:

```python
import sys, importlib.util, pathlib

BASE = pathlib.Path('/path/to/project')

def load_direct(module_name, file_path):
    spec = importlib.util.spec_from_file_location(
        module_name, file_path,
        submodule_search_locations=[]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load dependency-free modules
mymod = load_direct('app.mypackage.mymodule',
    BASE / 'app/mypackage/mymodule.py')
```

## Constraints

1. **Dependency order**: Load modules that the target depends on first.
2. **No `__init__.py` side-effects**: If your module references other modules via package imports (e.g. `from .other_module import X`), those imports still need to resolve. Use absolute imports or load dependencies first.
3. **Protocol-based dependencies**: For modules that depend on external classes (e.g. `MazdaSecurity`), define a `Protocol` with the required methods instead of importing the real class. This makes the module testable without the full dependency chain.
4. **Test runner**: Write a standalone `run_tests.py` that uses `load_direct` for all modules under test and runs `unittest` directly. Don't use pytest's collector — it triggers package imports.

## Example Pattern

```python
# Instead of:
from app.muts.security.security_engine import MazdaSecurity

# Do this in production code:
class MemoryPatchBackend(Protocol):
    def memory_patch_runtime(self, address: int, data: bytes) -> bool:
        ...

# Test uses MagicMock, production injects the real MazdaSecurity
```
