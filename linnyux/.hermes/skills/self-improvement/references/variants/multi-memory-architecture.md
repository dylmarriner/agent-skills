# Multi-Memory Architecture (from self-improving-agent)

An alternative approach to self-improvement that uses three distinct memory stores:

## Three Memory Types

### 1. Semantic Memory (`memory/semantic-patterns.json`)
Stores abstract patterns and rules reusable across contexts:
```json
{
  "patterns": {
    "pattern_id": {
      "id": "pat-2025-01-11-001",
      "name": "Pattern Name",
      "source": "user_feedback|implementation_review|retrospective",
      "confidence": 0.95,
      "applications": 5,
      "pattern": "One-line summary",
      "target_skills": ["debugger", "code-reviewer"]
    }
  }
}
```

### 2. Episodic Memory (`memory/episodic/`)
Stores specific experiences with timestamp, skill, situation, root_cause, solution, lesson.

### 3. Working Memory (`memory/working/`)
Stores current session context.

## Evolution Priority Matrix

| Trigger | Target Skill | Action |
|---------|--------------|--------|
| New PRD pattern discovered | prd-planner | Add to quality checklist |
| Architecture tradeoff clarified | architecting-solutions | Add to decision patterns |
| API design rule learned | api-designer | Update template |
| Debugging fix discovered | debugger | Add to anti-patterns |
| Review checklist gap | code-reviewer | Add checklist item |

## Self-Correction Workflow

Triggered when Bash returns non-zero or user reports wrong guidance:
1. Detect Error — capture context
2. Verify Root Cause — was skill guidance incorrect?
3. Apply Correction — update skill file with correction marker
4. Validate Fix — test corrected guidance

## Evolution Markers

```markdown
<!-- Evolution: 2025-01-12 | source: ep-2025-01-12-001 | skill: debugger -->
```
