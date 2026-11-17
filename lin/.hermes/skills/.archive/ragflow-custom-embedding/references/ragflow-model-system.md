# RAGFlow v0.26.3 Model Provider System

## Database Schema

RAGFlow v0.26.3 introduces a new multi-table model provider system alongside the legacy `tenant_llm` table.

### New Tables (created by `--init-model-provider-tables`)

```sql
-- Global factory definitions
llm_factories (name, tags, status, `rank`)
-- Global model definitions per factory  
llm (fid, llm_name, model_type, max_tokens, tags, is_tools)
-- Tenant-level provider (one per provider type per tenant)
tenant_model_provider (id, provider_name, tenant_id)
-- Unique: (tenant_id, provider_name)
-- Tenant-level instance (API key + endpoint per provider)
tenant_model_instance (id, instance_name, provider_id, api_key, status, extra)
-- Tenant-level model registration
tenant_model (id, model_name, provider_id, instance_id, model_type, status, extra)
```

### Legacy Tables (still used by some code paths)

```sql
tenant_llm (id, tenant_id, llm_factory, model_type, llm_name, api_key, api_base, max_tokens, used_tokens, status)
```

### Key Relationships

```
tenant_model_provider 1──* tenant_model_instance
tenant_model_provider 1──* tenant_model
tenant_model_instance  1──* tenant_model
```

### Model Name Format

The `embd_id` field in `tenant` and `knowledgebase` follows the format:
```
{model_name}@{instance_name}@{provider_name}
```

With 2 parts (`model@provider`): instance_name defaults to "default"
With 3 parts (`model@instance@provider`): all explicit

## Code Flow: get_model_config_from_provider_instance

1. `split_model_name(model_name)` → `(pure_model_name, instance_name, provider_name)`
2. `TenantModelProviderService.get_by_tenant_id_and_provider_name(tenant_id, provider_name)` → provider_obj
3. `_resolve_instance_for_model(provider_obj, instance_name, model_name)` → instance_obj
4. `TenantModelService.get_by_provider_id_and_instance_id_and_model_type_and_model_name(...)` → model_obj
5. **Lookup in `settings.FACTORY_LLM_INFOS`** (from llm_factories.json) → llm_info
6. Build model_config dict

**The hardcoded model list in `llm_factories.json` is the gatekeeper.** Even if the DB records are perfect, the model won't be found unless it's listed in this JSON file's per-factory `llm` array. This is the most common source of "Instance not found" errors.

## Peewee ORM Issues

- Peewee connection pooling can produce stale connections that don't see recently-inserted records
- Raw SQL queries work even when Peewee returns None
- Kill the task executor process (`pkill -f task_executor.py`) to force fresh connections
- Or restart the container: `docker restart docker-ragflow-cpu-1`
