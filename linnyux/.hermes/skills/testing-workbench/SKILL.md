---
name: testing-workbench
description: 'Testing strategy, patterns, and best practices across backend, frontend, and end-to-end testing.'
---

# Testing Workbench

Comprehensive testing strategies, patterns, and best practices.

## When to Use

Triggers:
- Need a testing strategy for a project
- Need testing patterns (Jest, factories, mocks)
- Designing comprehensive testing approaches
- Planning test strategies and test plans

## Workflows

### 1. Testing Patterns
See: `references/testing-patterns.md`
Jest testing patterns, factory functions, mocking strategies.

### 2. Testing Strategy Design
See: `references/testing-strategy-design.md`
Design comprehensive testing strategies for software quality.

### 3. Testing Strategist
See: `references/testing-strategist.md`
Design and implement comprehensive testing strategies.

### 4. Backend Testing
See: `references/backend-testing.md`
Write comprehensive backend tests including unit, integration, and E2E.


## Absorbed Skills

This umbrella absorbed the following sibling skills. Their unique value is now directly in this skill body:

| Absorbed Skill | Unique Content |
|---------------|----------------|
| testing-strategies | Test pyramid, unit/integration/E2E patterns, TDD cycle, AAA pattern, output format templates |
| testing-strategist | Comprehensive framework-specific guides (Jest, RTL, Playwright), mocking strategies, coverage config, test naming conventions |
| test-automator | Test coverage goals by type, framework quick reference, boilerplate generation scripts |
| test-engineering-suite | Contract testing, error path testing, Arrange-Act-Assert structure emphasis, anti-pattern checklist |

## Quick Reference

### Test Pyramid
- Unit: 70% (fast, isolated, pinpoint bugs)
- Integration: 20% (component interactions, API routes)
- E2E: 10% (critical user flows, slow but high confidence)

### AAA Pattern
- **Arrange**: Set up test environment and inputs
- **Act**: Call the function/trigger the action
- **Assert**: Verify the result

### Coverage Targets
- Global: 70-80% statements, branches, functions, lines
- Critical paths (auth, payments): 90%+
- Focus on meaningful tests, not chasing 100%

### Key Principles
- Test behavior, not implementation
- Write regression tests before fixing bugs (TDD)
- Mock at boundaries (APIs, filesystem), not your own code
- Keep tests deterministic, fast, and independent
- Test error paths, not just happy paths
