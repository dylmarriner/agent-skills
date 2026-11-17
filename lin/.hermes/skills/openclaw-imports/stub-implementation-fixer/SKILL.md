---
name: stub-implementation-fixer
description: Find and fix incomplete scaffolded implementations in a repository. Use when the user asks to replace TODOs, FIXMEs, stubs, placeholders, mock data, scaffold pages, or simplified code with real project-aligned implementations.
---

# Stub Implementation Fixer

Automatically finds and fixes incomplete implementations, scaffolded code, placeholder content, and mock data in repositories.

## When This Skill Activates

Use this skill when you need to:
- fix stubs, TODOs, FIXMEs, placeholders, or mock data
- replace scaffold pages or simplified implementations with real code
- audit a repository for incomplete implementation work
- clean up hardcoded demo content and convert it to project-aligned behavior

## Core Capability

**Detects patterns:**
- **Development markers:** `TODO`, `FIXME`, `XXX`, `HACK`, `BUG`, `DEPRECATED`
- **Implementation gaps:** functions throwing not-implemented errors, empty function bodies
- **Placeholder content:** "Scaffolded from...", "Website scaffold page", example.com, localhost
- **Mock/simplified code:** Hardcoded data, minimal business logic, fake implementations
- **Configuration stubs:** Default/example values that should be real values
- **Documentation gaps:** Empty README sections, placeholder documentation

**Implementation strategy:**
1. Analyze surrounding code to understand expected patterns
2. Check similar completed implementations in the codebase
3. Infer data structures from type definitions or existing usage
4. Follow project coding conventions and file structure
5. Replace mock data with realistic/production-ready content
6. Ensure implementations work (not just syntactically but semantically correct)

## Supported Scenarios

### 1. React/Next.js Scaffold Pages
**Detects:**
```typescript
export default function Page() {
  return <main><p>Scaffolded from the monorepo roadmap.</p></main>;
}
```
**Replaces with:** Full page implementation following project patterns

### 2. TODO and FIXME Markers
**Detects:**
```javascript
// TODO: Implement proper validation
// FIXME: This doesn't handle edge cases
function validateUser(data) {
  // not implemented yet
}
```

### 3. Mock Data and Simplified Code
**Detects:**
```javascript
const users = [
  { id: 1, name: 'John Doe', email: 'john@example.com' },
  { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
];
// This should be replaced with real API integration
```

### 4. Configuration Files with Placeholders
**Detects:** Placeholder values like `example.com`, `localhost`, `your-api-key-here`
**Replaces with:** Real configuration based on project context

### 5. Empty/Simplified Function Implementations
**Detects:**
```python
def process_data(data):
    # TODO: Implement this
    pass

def get_user_info(user_id):
    return {"name": "John", "email": "john@example.com"}  # Hardcoded
```

### 6. Documentation with Placeholder Content
**Detects:**
```markdown
# Project Name
Scaffolded from the monorepo roadmap.

## Installation

[Instructions here]
```

## Workflow Steps

### Phase 1: Discovery
1. **Scan codebase** for problematic patterns
2. **Classify findings** by type (TODOs, mocks, placeholders, simplified code)
3. **Analyze context** to understand expected implementation

### Phase 2: Implementation Strategy
1. **Pattern analysis** of similar completed code
2. **Mock data detection** - identifies fake/hardcoded data
3. **Type inference** from existing usage
4. **Auto-implementation** following project conventions
5. **Smart replacement** of mock content with realistic data

### Phase 3: Implementation
1. **Replace TODOs/FIXMEs** with actual implementations
2. **Transform mock data** into API calls or realistic data sources
3. **Implement placeholder functions** with proper business logic
4. **Update configuration** with real values
5. **Enhance simplified code** to production-ready quality

### Phase 4: Verification
1. **Second-pass audit** for missed stubs
2. **Integration testing** of replaced code
3. **Report generation** of all changes made

## Lessons Learned from Repo Audits

When this skill is used on a real repository, the highest-signal findings often come from patterns that are adjacent to stubs rather than literal TODOs:
- Broad `TODO`/`placeholder` searches are noisy because docs, tests, and fixtures often contain intentional examples. Narrow early to production code paths.
- Prioritize configuration fallbacks that hide misconfiguration, especially hardcoded localhost URLs, dev-only email services, and default API endpoints.
- In multi-tenant or scoped-data apps, look for primary-key lookups that skip ownership checks and for writes that reuse `userId` where a household/workspace/org id is expected.
- If the repository has authoritative product docs (roadmap, blueprint, UI spec), compare implemented flows against those docs before editing; the best fixes often come from contract drift rather than literal TODOs.
- Broad placeholder searches are noisy: many hits in screens, docs, and fixtures are intentional copy. Classify findings into “real implementation gap” vs “harmless text/example” before changing anything.
- If a file reveals a syntax breakage during inspection, verify the surrounding component or function signature before editing so the fix matches the local pattern.
- Prefer a two-pass workflow: first classify and fix safe issues, then rerun a targeted rescan to confirm the remaining hits are truly benign or require manual review.

## Safety Features

- **Idempotent operation** - Safe to run multiple times
- **Backup creation** - Original files backed up before significant changes
- **Scope awareness** - Works from project root for full context
- **Exclusion compliance** - Respects `.gitignore`, `node_modules/`, etc.
- **Change reporting** - Detailed log of all modifications
- **Rollback capability** - Can revert changes if needed

## Using the bundled scripts

Run the helpers from the repository root you want to inspect:

```bash
node /home/macuntu/.agents/skills/stub-implementation-fixer/scripts/scan.js .
node /home/macuntu/.agents/skills/stub-implementation-fixer/scripts/implement.js ./stub-scan-report.json . --dry-run
node /home/macuntu/.agents/skills/stub-implementation-fixer/scripts/index.js . --dry-run
```

Review the generated scan report before applying automatic changes to a real project.

## Pattern Detection

### Development Markers
- `TODO`, `FIXME`, `XXX`, `HACK`, `BUG`, `DEPRECATED`
- `STUB`, `MOCK`, `PLACEHOLDER`, `SCAFFOLDED`

### Mock Data Patterns
- Hardcoded user data with example.com emails
- Fake API responses
- Simplified business logic
- Placeholder database records

### Simplified Code
- Empty function implementations
- Minimal error handling
- Hardcoded return values
- Incomplete validation

### Placeholder Content
- Generic placeholder text
- Example configuration values
- Template documentation
- Scaffolded page content

## Output

The skill produces:
- **Enhanced codebase** with all stubs implemented
- **Mock data replaced** with realistic content
- **Comprehensive report** including:
  - Count of issues found and fixed by category
  - List of auto-fixed files
  - Files requiring manual review
  - Summary of implementation approaches used
  - Any edge cases or limitations encountered

## Implementation Quality

The skill ensures:
- **Production-ready code** - Not just syntactically correct
- **Consistent patterns** - Follows existing codebase style
- **Proper error handling** - Includes appropriate safeguards
- **Realistic data** - Mock replacements use contextually appropriate content
- **Type safety** - Preserves TypeScript types and interfaces
- **Test compliance** - Maintains or improves test coverage

## Examples

### Before (Mock Data)
```javascript
const apiService = {
  async getUsers() {
    return [
      { id: 1, name: 'John Doe', email: 'john@example.com' },
      { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
    ];
  }
};
```

### After (Real Implementation)
```javascript
const apiService = {
  async getUsers() {
    try {
      const response = await fetch('/api/users', {
        headers: {
          'Authorization': `Bearer ${process.env.API_TOKEN}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch users:', error);
      throw new Error('Unable to load users. Please try again later.');
    }
  }
};
```

## Troubleshooting

Complex scenarios requiring human judgment will be:
1. Logged with specific file and reason for manual review
2. Provided with suggested implementation approaches
3. Left as original for manual fixing
4. Included in the "Requires Manual Review" section

## Prerequisites

- Must be run from repository/project root
- Should have write access to project files
- Benefits from having git for backup/versioning
- Works best in projects with established patterns
