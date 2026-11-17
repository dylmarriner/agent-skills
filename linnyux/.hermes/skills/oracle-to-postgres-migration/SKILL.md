---
name: oracle-to-postgres-migration
description: 'Complete toolkit for migrating Oracle databases to PostgreSQL: master planning, stored procedure translation, integration testing, bug reporting, and code review.'
---

# Oracle to PostgreSQL Migration

Comprehensive migration toolkit covering the full lifecycle from planning to verification.

## When to Use

Triggers:
- Starting a multi-project Oracle-to-PostgreSQL migration
- Converting Oracle stored procedures to PL/pgSQL
- Creating integration tests for migrated data access
- Reporting migration defects
- Reviewing migration code for risks

## Workflows

### 1. Master Migration Planning
See: `references/master-migration-plan.md`
Discover all projects in a .NET solution, classify each for migration eligibility.

### 2. Stored Procedure Translation
See: `references/stored-procedures-translation.md`
Translate PL/SQL to PL/pgSQL preserving method signatures and type-anchored parameters.

### 3. Integration Test Project Scaffolding
See: `references/integration-test-scaffolding.md`
Scaffold xUnit integration test project for validating migrated data access.

### 4. Integration Test Creation
See: `references/integration-test-creation.md`
Create integration test cases for .NET data access artifacts.

### 5. Integration Testing Plan
See: `references/integration-testing-plan.md`
Create plan for .NET data access migration testing.

### 6. Bug Reports
See: `references/migration-bug-report.md`
Create structured bug reports for defects found during Oracle-to-PostgreSQL migration.

### 7. Code Review
See: `references/migration-code-review.md`
Identify migration risks by cross-referencing Oracle vs PostgreSQL data access patterns.
