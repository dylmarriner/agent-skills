# Reverse Engineering Methodology

Structured approach for analyzing software targets of any complexity.

## 1. Objective Definition

- Establish: target, platform, architecture, operating environment
- Identify: available artifacts, constraints, authorization scope
- Classify analysis type: static, dynamic, behavioral, comparative, protocol, firmware

## 2. Investigation Plan

- Build structured plan before drawing conclusions
- Prioritize steps by information gain vs effort
- Identify dependencies between analysis phases

## 3. Evidence Collection

Examine ALL available evidence:
- Executables, libraries, bytecode, scripts, firmware
- Memory dumps, packet captures, logs, configuration files
- Symbols, strings, metadata, resources, documentation
- Control flow, data flow, call graphs, imports/exports
- System calls, APIs, memory allocation, threading
- Exception handling, serialization, encryption, compression
- Compiler patterns, calling conventions, ABI details
- Obfuscation, packing, anti-debugging, virtualized code

## 4. Architecture Reconstruction

- Identify components, states, data structures, algorithms
- Map interfaces, dependencies, trust boundaries
- Document execution flow at module, function, and instruction level
- Translate low-level behavior to clear pseudocode

## 5. Evidence Ledger

Tag every conclusion with its confidence level:

| Level | Meaning |
|-------|---------|
| Confirmed | Verifiable by multiple independent signals |
| High | Strong evidence, single source |
| Medium | Plausible inference, needs verification |
| Low | Speculative, needs experiment |
| Unknown | No evidence yet; propose fastest resolving experiment |

## 6. Cross-Validation

- Cross-check findings using independent signals
- Never rely on a single observation for critical conclusions
- State uncertainty precisely — do not invent missing evidence

## 7. Root-Cause Focus

- Prioritize understanding WHY over superficial pattern matching
- Reconstruct the developer's intent, constraints, and assumptions
- Document security-relevant behavior, implementation weaknesses, trust boundaries

## 8. Reproducibility

- Include exact commands, offsets, signatures, verification procedures
- Produce findings another skilled engineer can independently reproduce
- Prefer automated, repeatable analysis with manual verification of critical conclusions
