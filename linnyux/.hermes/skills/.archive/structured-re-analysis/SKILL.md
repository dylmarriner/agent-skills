---
category: cybersecurity-skills
description: Structured methodology for reverse-engineering binaries, firmware, protocols, and crypto implementations. Ensures reproducible, evidence-driven analysis with clear confidence levels and prioritized next steps.
name: structured-re-analysis
trigger: User provides a binary, firmware dump, protocol capture, encrypted file, or installer for reverse engineering. Apply when analyzing any unknown target, especially commercial service tools, mobile repair software, or protected executables.
---

# Structured Reverse Engineering Analysis

Class-level methodology for approaching any RE target systematically. Adapted from professional RE workflow and this user's quality standards.

## Framework (apply in order)

### 1. Objective
Define the precise RE goal. One sentence. What must we determine?

### 2. Initial Assessment
Summarize the target in a table:

| Property | Value |
|----------|-------|
| **Platform** | OS, arch, bitness |
| **Size** | File size |
| **Installer type** | Inno Setup, SIM, NSIS, custom |
| **Protection** | UPX, Themida, custom packer |
| **Language** | Delphi, C/C++ Qt, .NET, Go, Rust |
| **Key unknowns** | What we need to figure out |

### 3. Investigation Plan
Prioritized step-by-step strategy. Order matters:
1. Structural analysis (file format, sections, overlay)
2. Signature/entropy scan (known patterns, packers, crypto)
3. String extraction (URLs, API paths, keys, error messages)
4. Import/export table analysis (system calls, crypto libs)
5. Dynamic analysis (if possible — Wine, VM, debugger)
6. Protocol reconstruction (network captures, API monitoring)
7. Crypto constant extraction (IVs, keys, salts, algorithm IDs)

### 4. Technical Analysis
Present findings with:
- Exact offsets, addresses, sizes
- Pseudocode for complex logic
- Protocol message formats
- Data structure definitions
- Crypto algorithm identification (not just "uses encryption")

### 5. Evidence & Confidence Table
For EACH major finding, rate confidence:

| Finding | Evidence | Confidence |
|---------|----------|------------|
| Confirmed | Multiple independent signals | ✅ Confirmed |
| Strong inference | Consistent indirect evidence | 📊 High |
| Hypothesis | Fits but unproven | 🔬 Medium |
| Unknown | Needs experiment | ❓ Low |

Distinguish carefully. Don't claim confirmed when you only have a hypothesis.

### 6. Reconstructed Design
Describe architecture in terms of:
- Components and their relationships
- Data flow between components
- State machine / execution sequence
- Trust boundaries and authentication layers

### 7. Security & Reliability Findings
Document:
- Hardcoded credentials, keys, tokens
- Weak crypto implementations
- Vulnerable dependency versions (e.g., OpenSSL 1.0.1m)
- Anti-debugging / anti-analysis mechanisms
- Trust model weaknesses

### 8. Reproduction Procedure
Steps another engineer can follow to independently verify:
- Exact commands with flags
- Tool names and versions
- Offsets and addresses
- Extraction criteria (what to search for, how to confirm)

### 9. Next Actions
Highest-value experiments to resolve unknowns:
- What additional artifact would unlock the next stage
- What dynamic analysis would fill the gap
- Which specific tool or approach to try next

## This User's Style Preferences

- **Execution over description**: Build the tool, don't describe building it. Working artifacts over analysis reports.
- **Minimal verbosity**: State findings directly. Don't recap what was already established.
- **"Take your pick"**: When given options, choose the best one and execute — don't ask which path to take.
- **Evidence-driven**: Confidence levels for every claim. Distinguish hypothesis from confirmed fact.
- **Prefer automation**: Script repeatable steps. Manual verification only for critical conclusions.
- **No stubs**: Every function must be real. No TODOs, NotImplementedError, or placeholder implementations.
