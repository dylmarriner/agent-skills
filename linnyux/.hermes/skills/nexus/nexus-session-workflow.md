# Nexus Session Workflow

## Session Start
1. Call `agent_context("hermes:kubuntu-desktop")` to get current state
2. Call `memory_recall(query="current task: {project}", limit=5)` to resume work

## During Work
1. Save decisions: `memory_save(content="Decided to use X because Y", importance=0.7)`
2. Save lessons: `memory_save(content="Learned: X approach fails when Y", importance=0.9, tags=["lesson"])`
3. Save user prefs: `memory_save(content="User prefers X over Y", importance=0.8, tags=["preference"])`

## Session End
1. Save session summary: `memory_save(content="Completed: {summary}", importance=0.6)`
2. Save handoff notes if another agent needs to continue

## Cross-Session
Nexus persists across all sessions. Always recall before assuming context.
