# Tiered Storage (from self-improving-1-2-3)

Alternative lightweight approach using `~/self-improving/` directory:

## Tier Structure

| Tier | Location | Size Limit | Behavior |
|------|----------|------------|----------|
| HOT | ~/self-improving/memory.md | <=100 lines | Always loaded |
| WARM | ~/self-improving/projects/, domains/ | <=200 lines each | Load on context match |
| COLD | ~/self-improving/archive/ | Unlimited | Load on explicit query |

## Automatic Promotion/Demotion
- Pattern used 3x in 7 days → promote to HOT
- Pattern unused 30 days → demote to WARM
- Pattern unused 90 days → archive to COLD

## Namespace Isolation
- Project patterns stay in `projects/{name}.md`
- Global preferences in HOT tier
- Domain patterns (code, writing) in `domains/`
- Cross-namespace inheritance: global → domain → project

## Conflict Resolution
1. Most specific wins (project > domain > global)
2. Most recent wins (same level)
3. If ambiguous → ask user

## Quick Queries
| User says | Action |
|-----------|--------|
| "What do you know about X?" | Search all tiers for X |
| "What have you learned?" | Show last 10 from corrections.md |
| "Memory stats" | Show counts per tier |
| "Forget X" | Remove from all tiers (confirm first) |
