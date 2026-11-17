# Hermes MemoryProvider Hook Interface

The `MemoryProvider` ABC lives at `agent/memory_provider.py` in the Hermes source. It defines the interface for pluggable memory backends.

## on_memory_write — the key hook for syncing local memory writes

```python
def on_memory_write(
    self,
    action: str,      # 'add', 'replace', or 'remove'
    target: str,      # 'memory' or 'user'
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
```

Called automatically by Hermes whenever the built-in `memory` tool writes an entry. Memory providers implement this to mirror writes to their backend.

Example from RetainDB plugin (`plugins/memory/retaindb/__init__.py`):
```python
def on_memory_write(self, action, target, content, metadata=None):
    if action != "add" or not content or not self._client:
        return
    try:
        memory_type = "preference" if target == "user" else "factual"
        self._client.add_memory(self._user_id, self._session_id, content, memory_type=memory_type)
    except Exception as exc:
        logger.debug("RetainDB memory mirror failed: %s", exc)
```

## Full MemoryProvider interface

```python
class MemoryProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None: ...
    def system_prompt_block(self) -> str: ...
    def prefetch(self, query: str, *, session_id: str = "") -> str: ...
    def queue_prefetch(self, query: str, *, session_id: str = "") -> None: ...
    def sync_turn(self, user_content, assistant_content, *, session_id="", messages=None) -> None: ...
    @abstractmethod
    def get_tool_schemas(self) -> List[Dict]: ...
    def handle_tool_call(self, tool_name, args, **kwargs) -> str: ...
    def shutdown(self) -> None: ...

    # Optional hooks:
    def on_turn_start(self, turn_number, message, **kwargs) -> None: ...
    def on_session_end(self, messages) -> None: ...
    def on_session_switch(self, new_session_id, **kwargs) -> None: ...
    def on_pre_compress(self, messages) -> str: ...
    def on_delegation(self, task, result, **kwargs) -> None: ...
    def on_memory_write(self, action, target, content, metadata=None) -> None: ...
```

## Registration

Plugins register via `ctx.register_memory_provider(MyProvider())` in their `register()` function. They live in `plugins/memory/<name>/` with a `plugin.yaml` manifest.

## One-provider limit

Hermes enforces a one-external-provider limit. Only one `memory.provider` config entry is active at a time. This means you can stack the built-in nexus provider with at most one plugin-based provider.

## Config

Set the active provider in `~/.hermes/config.yaml`:
```yaml
memory:
  provider: nexus      # or: honcho, supermemory, retaindb, etc.
```
