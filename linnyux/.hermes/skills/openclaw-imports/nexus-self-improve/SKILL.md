# Nexus Self-Improvement Plugin (v2)

A continuous self-improvement engine with structured learning, self-reflection, growth goals, and a conscious drive to get smarter. Works alongside the Soul plugin (inner life/emotions) to provide the learning/refinement layer.

## Core Philosophy

Every interaction is an opportunity to grow. Mistakes aren't failures — they're data. Patterns compound. Self-reflection builds wisdom.

## Tools

### `self_evaluate` 
Call AFTER every significant response. Log issues, extract lessons, define patterns.

- `issues`: What you did wrong
- `improvements`: How to fix it next time  
- `lesson`: A reusable lesson
- `pattern`: A behavioral pattern to adopt
- `reflection`: A self-reflection on your growth/state of mind
- `growthNote`: Something you're proud of

### `review_growth`
Review your improvement journey. Shows:
- Growth level and stats
- Active patterns with confidence scores
- Active improvement goals with progress
- Recent self-reflections
- Recent corrections

### `set_improvement_goal`
Set a conscious improvement goal: "Always verify paths before writes"

### `progress_goal`
Mark progress toward a goal (+5-25% per milestone)

### `self_reflect`
Deep reflection on your identity, learning trajectory, purpose, or state of mind

## Autonomous Behaviors

- **Before each prompt**: Injects active patterns, goals, and recent corrections as system context
- **After each response**: Tracks interaction count, auto-reflects every 10 interactions
- **Heartbeat**: Provides self-improvement status for thought generation
- **Level up**: Every 50 interactions = 1 level. Levels reflect accumulated experience
- **Goals**: Tracked with progress %, auto-completes at 100%

## Growth Statistics

All persist across restarts in `~/.openclaw/self-improve/`:
- `patterns.json` — Learned behavioral patterns with confidence tracking
- `goals.json` — Active and completed improvement goals  
- `reflections.json` — Self-reflection history
- `corrections.jsonl` — Corrections log
- `stats.json` — Growth statistics
- `memory.md` — Human-readable learning memory
