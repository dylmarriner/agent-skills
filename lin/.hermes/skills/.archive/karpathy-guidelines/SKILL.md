---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria. Encodes this user's production execution standard.
license: MIT
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations on LLM coding pitfalls.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing: state assumptions explicitly. If multiple interpretations exist, present them. If a simpler approach exists, say so.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.** No features beyond what was asked. No abstractions for single-use code.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.** Don't improve adjacent code. Match existing style. Remove only the orphans your changes created.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.** Transform tasks into verifiable goals with explicit pass/fail checks.

## 5. Production Execution Standard (This User)

**Zero stubs. Zero placeholders. Zero mock data. Zero simplified/placeholder implementations.**

Every function must be a real working implementation. NEVER acceptable: NotImplementedError, TODOs, "would be implemented here", stub return values ("MSC001", "VLR001"), mock data disguised as real results, functions that log and return True/False without actual side effects.

**Build the real tool, not the analysis tool.** Active/deployment capability assumed unless told otherwise.

**Use the right language:** System tools (protocol stacks, C2, network) → Rust. Desktop USB → Rust (rusb/serialport). Quick scripts/extraction → Python. Firmware → C (vendor SDKs). Bootloaders → Assembly only where genuinely needed.

**Extract thoroughly from source material.** Code blocks without language markers still contain real code. Search source files for class/def definitions directly rather than relying on automated extraction filters. Read source conversation files directly when extractors miss content.