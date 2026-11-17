---
name: dataverse-python-sdk
description: Complete Dataverse Python SDK toolkit for CRUD operations, bulk operations, paging, advanced patterns, and use-case-specific implementations. Use when working with Microsoft Dataverse through Python SDK.
license: MIT
---

# Dataverse Python SDK Toolkit

Complete Dataverse Python SDK toolkit covering all aspects of Dataverse integration from basic CRUD to advanced patterns and bulk operations. These frameworks are tested across production Dataverse integrations.

## When to Use

**Triggers:**
- Creating Python integrations with Dataverse
- Performing CRUD operations on Dataverse entities
- Bulk importing/exporting data
- Implementing complex queries with paging
- Building specific use-case solutions

**Context:**
- Python applications interacting with Dataverse
- Custom data integration layers
- Data migration scenarios
- Real-time Dataverse access patterns

---

## Table of Contents

1. [SDK Setup & Quickstart](#1-sdk-setup--quickstart)
2. [Production Code Patterns](#2-production-code-patterns)
3. [Advanced Patterns](#3-advanced-patterns)
4. [Use-Case Builders](#4-use-case-builders)

---

## 1. SDK Setup & Quickstart

### Installation & Configuration

**Install the SDK:**
```bash
pip install msdataverse
```

**Configuration:**
```python
from dataverse import DataverseClient, AuthenticationConfig

config = AuthenticationConfig(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

client = DataverseClient(config)
```

**Basic CRUD Operations:**

```python
# Create
user = client.create(
    entity_name="account",
    data={
        "name": "Contoso",
        "address_line1": "123 Main St"
    }
)

# Read
account = client.read(
    entity_name="account",
    id=user.id
)

# Update
updated = client.update(
    entity_name="account",
    id=user.id,
    data={
        "name": "Contoso Updated"
    }
)

# Delete
client.delete(
    entity_name="account",
    id=user.id
)
```

**Query Operations:**
```python
# Fetch collection
accounts = client.query(
    entity_name="account",
    filter='status eq "Active"'
)

# Fetch single record
account = client.get_single(
    entity_name="account",
    filter="name eq 'Contoso'"
)
```

---

## 2. Production Code Patterns

### Error Handling

```python
from dataverse import DataverseException

try:
    account = client.create(
        entity_name="account",
        data={"name": "Contoso"}
    )
except DataverseException as ex:
    logger.error(f"Dataverse error: {ex}")
    # Handle specific error codes
    if ex.error_code == "duplicate_key":
        # Handle duplicate
        pass
```

### Connection Pooling

```python
from dataverse import DataverseClientPool

pool = DataverseClientPool(
    config=auth_config,
    max_connections=10
)

with pool.get_client() as client:
    account = client.create(...)
# Connection automatically returned to pool
```

### Retry Logic

```python
from dataverse import RetryPolicy, ExponentialBackoff

retry_policy = RetryPolicy(
    max_retries=3,
    backoff=ExponentialBackoff(base_delay=1000, max_delay=30000)
)

client = DataverseClient(auth_config, retry_policy=retry_policy)
```

### Logging & Diagnostics

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('dataverse.integrations')
```

---

## 3. Advanced Patterns

### Bulk Operations

```python
# Bulk create
accounts = [
    {"name": f"Account {i}", "status": "Active"}
    for i in range(1000)
]

batch = client.bulk_create(
    entity_name="account",
    data=accounts,
    batch_size=200
)

# Bulk update
updates = [
    {"id": id, "data": {"status": "Inactive"}}
    for id in closed_account_ids
]

client.bulk_update(
    entity_name="account",
    updates=updates,
    batch_size=100
)
```

### Paging and Large Datasets

```python
# Pagination handler
def fetch_all_accounts():
    all_records = []
    page = 1
    
    while True:
        batch = client.query(
            entity_name="account",
            filter="",
            top=1000,
            skip=(page - 1) * 1000
        )
        
        if not batch:
            break
            
        all_records.extend(batch)
        
        if len(batch) < 1000:
            break
            
        page += 1
    
    return all_records
```

### Transactional Operations

```python
from dataverse import Transaction

with client.transaction() as tx:
    try:
        # Create account
        account = tx.create("account", {"name": "Parent"})
        
        # Create related contacts
        contacts = [
            tx.create("contact", {"name": "Contact 1", "parent_account": account.id})
            for _ in range(3)
        ]
        
        # Commit if all succeed
        tx.commit()
    
    except Exception as e:
        tx.rollback()
        raise
```

### Caching Strategies

```python
from dataverse import CacheConfig, RedisCache

cache = RedisCache(host="localhost", port=6379)

# Cached read
account = client.cached_read(
    entity_name="account",
    id="account-id",
    cache=cache,
    ttl_seconds=3600
)
```

---

## 4. Use-Case Builders

### CRM Data Sync Pattern

```python
class CrmDataSync:
    def __init__(self, client):
        self.client = client
        self.cache = MemoryCache()
    
    def sync_accounts(self, external_data):
        """Sync external CRM data to Dataverse."""
        for record in external_data:
            existing = self.cache.get(record.id)
            
            if existing:
                self._update_account(record, existing)
            else:
                self._create_account(record)
    
    def _create_account(self, record):
        return self.client.create(
            entity_name="account",
            data={
                "name": record.name,
                "industry": record.industry,
                "annual_revenue": record.revenue
            }
        )
    
    def _update_account(self, record, existing):
        return self.client.update(
            entity_name="account",
            id=existing.id,
            data={
                "name": record.name,
                "last_synced": datetime.now()
            }
        )
```

### Data Migration Pattern

```python
class DataMigration:
    def __init__(self, client, source_system):
        self.client = client
        self.source = source_system
        self.batch_size = 500
        self.success_count = 0
        self.failure_count = 0
    
    def migrate_contacts(self):
        """Migrate contacts from legacy system to Dataverse."""
        legacy_contacts = self.source.fetch_all_contacts()
        
        for batch in self._chunk(legacy_contacts, self.batch_size):
            self._process_batch(batch)
    
    def _process_batch(self, contacts):
        for contact in contacts:
            try:
                self.client.create("contact", self._transform(contact))
                self.success_count += 1
            except Exception as e:
                self._log_error(contact, e)
                self.failure_count += 1
    
    def _transform(self, legacy_contact):
        return {
            "first_name": legacy_contact.fname,
            "last_name": legacy_contact.lname,
            "email": legacy_contact.email,
            "phone": legacy_contact.phone
        }
```

---

## Common Mistakes

**DON'T: Not handle pagination properly**
```python
# BAD - Only fetches first batch
records = client.query(..., top=100)

# GOOD - Fetches all records with paging
all_records = []
skip = 0
while True:
    batch = client.query(..., top=100, skip=skip)
    if not batch:
        break
    all_records.extend(batch)
    skip += len(batch)
```

**DON'T: Ignore error handling**
```python
# BAD - No error handling
client.create(...)

# GOOD - Handle errors
try:
    client.create(...)
except DataverseException as ex:
    logger.error(ex)
```

**DON'T: Block long operations**
```python
# BAD - Blocking synchronous calls
data = client.query_sync(...)

# GOOD - Use async where possible
data = await client.query_async(...)
```

---

## Quick Reference

**Basic Operations:**
- Create: `client.create(entity_name, data)`
- Read: `client.read(entity_name, id)`
- Update: `client.update(entity_name, id, data)`
- Delete: `client.delete(entity_name, id)`
- Query: `client.query(entity_name, filter, top, skip)`

**Bulk Operations:**
- Bulk Create: `client.bulk_create(entity_name, data, batch_size)`
- Bulk Update: `client.bulk_update(entity_name, updates, batch_size)`
- Bulk Delete: `client.bulk_delete(entity_name, ids, batch_size)`

**Advanced Features:**
- Transactions: `with client.transaction() as tx`
- Pagination: Use `top` and `skip` parameters
- Caching: Use `cached_read()` method
- Retry: Configure `RetryPolicy`

**Error Handling:**
- `DataverseException` base class
- `DuplicateKeyException` for duplicates
- `RecordNotFoundException` for missing records
- `AuthenticationException` for auth errors

---

*Complete Dataverse Python SDK toolkit consolidating all Python Dataverse development patterns including setup, CRUD operations, bulk operations, advanced patterns, and use-case-specific implementations. All Dataverse Python skills merged into one library for production-level Dataverse integrations.*