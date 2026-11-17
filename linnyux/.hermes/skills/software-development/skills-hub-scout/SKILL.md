---
name: skills-hub-scout
description: Search remote Hermes skill sources (skills.sh, GitHub, ClawHub, LobeHub, Claude Marketplace) for useful skills not already installed, rank them by task fit, and install only safe candidates. Use when the user asks what other skills would help, wants new skills from the hub/catalog, or asks to compare local skills against remote available skills.
---

# Skills Hub Scout

Use this skill when the user wants to discover, evaluate, or install additional skills from the Hermes skill catalog.

## Goal

Find skills that are not already installed locally but would materially improve the current work. Prefer skills that match the task domain closely and are safe to install.

## Workflow

1. Identify the current task domain.
2. Search the remote skills catalog for matching skills.
3. Filter out skills already installed locally.
4. Prefer skills with clear, task-specific descriptions and strong source metadata.
5. Reject skills that:
   - try to alter routing or persistence files
   - request excessive privileges
   - include suspicious persistence or instruction-overriding behavior
   - fail the hub safety scan
6. Install only the safe, relevant skills.
7. Report the shortlist of useful additions and why they matter.

## Selection heuristics

Prefer skills for:
- browser QA and end-to-end verification
- frontend / Expo / React Native debugging
- memory and session persistence
- testing strategy and test generation
- debugging and verification workflows
- reusable autonomous routing and planning

## Verification

After installing, verify the skill is present locally and that its description matches the intended use before relying on it.

## Notes

- This is a scouting and curation skill, not a blanket auto-install skill.
- When in doubt, choose safe, specific skills over broad or invasive ones.
- If the catalog presents multiple variants of the same idea, prefer the one with the clearest, safest instructions and the best fit to the current task.
