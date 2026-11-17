# Nexus Feature Integration Patterns

## Architecture
Nexus runs on kubuntux at 100.93.75.87:7777
- FastAPI + PostgreSQL (asyncpg) + Redis + SQLAlchemy ORM
- Docker Compose stack with 4 containers
- Volume mounts for live code (`. :/app:ro`)

## Adding Features

### 1. Database Models (schema.py)
Add new SQLAlchemy models with UUID primary keys:
```python
class MyModel(Base):
    __tablename__ = "my_models"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```
The `Base.metadata.create_all()` at startup auto-creates tables.

### 2. Migration SQL (main.py _run_migrations)
For complex tables, add raw SQL with `CREATE TABLE IF NOT EXISTS` and `DEFAULT gen_random_uuid()`:
```sql
CREATE TABLE IF NOT EXISTS my_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
)
```

### 3. FastAPI Router
```python
router = APIRouter()
@router.post("/endpoint")
async def handler(body: dict, db: AsyncSession = Depends(get_db)):
    # Use body.get("key") for all fields
    ...
```

### 4. Register in main.py
```python
from app.routers.my_module import router as my_router
app.include_router(my_router, prefix="/v1/my", tags=["my"], dependencies=[Depends(_verify_key)])
```

### 5. MCP Tools (mcp.py)
Add tool schema to TOOLS list with inputSchema. Add dispatch handler in _dispatch().

## Common Failure Patterns & Fixes

| Problem | Symptom | Fix |
|---------|---------|-----|
| UUID null violation | `null value in column "id"` | Add `gen_random_uuid()` to INSERT or `DEFAULT gen_random_uuid()` to table |
| JSONB list error | `'list' object has no attribute 'encode'` | `json.dumps()` the list before passing as param |
| JSONB bind error | `could not determine data type of parameter` | Use `CAST(:param AS jsonb)` not `:param::jsonb` |
| function/syntax error | `syntax error at or near ":"` | Don't use PostgreSQL `::` cast syntax inside SQLAlchemy text() with bind params |
| FastAPI 422 for POST | `Input should be a valid list` | Don't mix path params with multiple body params — use `body: dict` |
| Container not seeing changes | Old code running | Add `volumes: - .:/app:ro` to docker-compose, restart containers |
| Pycache issues | Still running old code after volume mount | `find /app -name __pycache__ -exec rm -rf {} +` inside container |

## Restart After Changes
```bash
docker restart nexus-nexus-api-1
# Wait 8s for health check
curl -s http://localhost:7777/health
```
