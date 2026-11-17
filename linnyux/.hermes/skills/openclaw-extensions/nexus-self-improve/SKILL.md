# Nexus Self-Improvement Plugin

A continuous self-improvement engine that runs inside Nexus. Evaluates responses, tracks mistakes, extracts reusable patterns, and compounds learnings across sessions.

## Tools

### `self_evaluate`
Call this after responding to a user, especially when:
- You make a mistake or the user corrects you
- You complete significant work
- You notice suboptimal output
- The user says "learn from that" or "improve"

Parameters:
- `responseType`: Type of response (advice, code, explanation, etc.)
- `issues`: Array of issues you noticed
- `improvements`: How to improve next time
- `lesson`: A reusable lesson from this interaction
- `pattern`: A behavioral pattern to adopt

### `review_patterns`
Check what you've learned. Use before:
- Starting significant work
- When unsure about past learnings
- To remind yourself of patterns

### `reset_learning`
Clear all learning data and archive it. Requires `confirm: true`.

## Autonomous Behavior

The plugin automatically:
- **Before each prompt**: Injects remembered patterns and recent corrections as system context
- **After each response**: Tracks interaction count, triggers consolidation every N turns
- **On gateway start**: Loads persistent learning store from disk

## Data Storage

All data lives in `~/.openclaw/self-improve/`:
- `memory.md` — Active lessons and patterns
- `corrections.jsonl` — Recent corrections log
- `patterns.json` — Structured pattern database
- `stats.json` — Learning statistics
- `archive/` — Archived snapshots of old data

## Best Practices

- Call `self_evaluate` proactively after responses
- Extract concrete lessons, not vague observations
- Patterns should be actionable: "When X happens, do Y"
- Review patterns before starting complex work
- Data persists across restarts — learning compounds
