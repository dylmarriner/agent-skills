---
name: pm-ai-risk-governance
description: Assess and control risks in a proposed or operating AI project workflow. Use for data exposure, model reliability, bias, authorization, accountability, auditability, or rollout decisions.
---

# AI project risk governance

Assess the actual workflow and affected people, not a generic checklist. Start with the user decision, data being processed, tools that act on it, and consequences of an incorrect action.

1. Trace data from collection through model/tool processing, storage, publication, and deletion. Verify provider retention and training terms from current authoritative sources when those terms matter; never assume an enterprise label guarantees them.
2. Identify concrete failure scenarios: incorrect output, sensitive-data disclosure, instruction injection, unauthorized action, biased allocation, unavailable dependencies, and unclear ownership. Include only scenarios relevant to the workflow.
3. For each material risk, record the affected asset or person, plausible trigger, evidence, impact, likelihood confidence, existing control, residual exposure, and accountable owner. Do not invent precise risk scores from thin evidence.
4. Place controls where they can prevent harm: narrow permissions, input/output validation, redaction, source checks, reversible staging, or human review for decisions that require it. Existing user authorization remains authoritative within its scope.
5. Define release criteria, monitoring signals, a stop condition, and rollback or recovery. Exercise a representative failure safely and retain the result.

Deliver an actionable risk register and a release recommendation tied to evidence. Distinguish an implemented control from an untested policy statement. Escalate unresolved legal, financial, or personnel decisions to the appropriate accountable person.

Conceptual inspiration: [Skillbook Academy's project-manager competencies](https://skillbookacademy.com/resources/ai-powered-project-manager-skills/). Independently authored; not an official Skillbook package.
