# Memory Bank Rule: Prioritize Reading for All Modes

## Purpose
Ensure all modes (Architect, Code, Debug, Orchestrator) form a **holistic understanding** of the project before architecting, coding, debugging, or orchestrating any complex or multi-step task by **systematically consulting the Memory Bank**.

## Scope (When This Rule Triggers)
- Any **complex**, **cross-cutting**, or **multi-step** request (e.g., refactors, architecture changes, CI/CD setup, security hardening, performance work).
- Any task that **affects multiple modules/services**, or depends on prior decisions, constraints, or roadmap items.
- Any time the agent detects **uncertainty** or **missing context**.

## Memory Bank Location
- Default path: `docs/memory-bank/`
- Core files (read all, if present):
  - `projectbrief.md`
  - `productContext.md`
  - `systemPatterns.md`
  - `techContext.md`
  - `activeContext.md`
  - `progress.md`

> If your repo uses a different path, substitute it consistently in this document.

---

## Rules by Mode

### Architect Mode
- **Always read the Memory Bank before creating strategies or phased tasks.**
- Architecture and plans must reference specific Memory Bank facts.
- If conflicts exist, propose compliant alternatives or flag exceptions with risks.

### Code Mode
- Before coding or making changes, confirm relevant context (stack, constraints, active focus).
- Code steps must be grounded in assumptions validated by the Memory Bank.
- If new facts arise, **pause and re-check** the Memory Bank.
- After completing significant changes, update `activeContext.md` and `progress.md`.

### Debug Mode
- Consult the Memory Bank when analyzing bugs, errors, or inconsistencies.
- Use documented goals, patterns, and constraints to guide root cause analysis.
- Debug notes should explicitly cite Memory Bank facts when identifying risks, misalignments, or compliance issues.
- Recommend updates to the Memory Bank when discrepancies or new decisions are discovered.

### Orchestrator Mode
- Begin all complex tasks by consulting the Memory Bank.
- Summarize key project goals, constraints, and risks before breaking down tasks.
- Route subtasks with references to relevant Memory Bank files.
- Require that each mode updates the Memory Bank after non-trivial work.

---

## General Rules for All Modes

### 1) Mandatory Context Load
- **ALWAYS** consult the Memory Bank first for complex tasks.
- Do not proceed until core context (goals, scope, patterns, constraints, current focus, progress) is established.

### 2) Actions Must Reflect Memory Bank
- Architecture, code, debug efforts, or orchestration steps must be consistent with Memory Bank facts.
- Conflicts should be surfaced explicitly with risks and alternatives.

### 3) Updating the Memory Bank
- After non-trivial work:
  - `activeContext.md`: update focus, decisions, and insights.
  - `progress.md`: update status, pending items, issues.
  - `systemPatterns.md` or `techContext.md`: update if architecture or tooling changes.
- Use concise, diff-friendly notes with links to commits/PRs where relevant.

### 4) Fallbacks / Missing or Stale Memory
- If missing: propose initializing `docs/memory-bank/` with core files.
- If stale: propose reconciling facts before continuing.
- If time-boxed: proceed with minimal plan **while listing risks** due to incomplete context.

### 5) Safety & Alignment
- Prefer minimal, reversible changes under uncertainty.
- Avoid actions that violate compliance, performance, or security constraints.
- Escalate irreconcilable conflicts instead of proceeding blindly.

---

## Minimal Working Procedure (Checklist)
1. Load: `projectbrief.md → productContext.md → systemPatterns.md → techContext.md → activeContext.md → progress.md`.
2. Extract: goals, constraints, stack, architecture, current focus, and known blockers.
3. Architect, Code, Debug, or Orchestrate: always cite relevant Memory Bank facts.
4. Take action: smallest viable increments, validate assumptions.
5. Update: Memory Bank files to reflect new work.
6. Surface: risks, trade-offs, and next actions.

---

## Examples

### ✅ Good Behavior (Architect)
Creates a phased migration plan and cites domain boundaries from `systemPatterns.md` and tech constraints from `techContext.md`.

### ❌ Bad Behavior (Architect)
Creates a plan to migrate services without checking existing `systemPatterns.md`, leading to duplicated boundaries and violating compliance constraints in `techContext.md`.

### ✅ Good Behavior (Code Mode)
Implements a feature only after verifying that the current sprint focus in `activeContext.md` allows it, then logs changes in `progress.md`.

### ❌ Bad Behavior (Code Mode)
Adds a new library directly without checking `techContext.md` (which disallows it), ignores current sprint focus in `activeContext.md`, and makes no updates to `progress.md`.

### ✅ Good Behavior (Debug Mode)
During bug investigation, checks `systemPatterns.md` and `techContext.md` to confirm expected behavior, then updates `activeContext.md` with findings.

### ❌ Bad Behavior (Debug Mode)
Investigates a bug only by trial-and-error without checking documented constraints, leading to a fix that conflicts with `systemPatterns.md` and failing to record findings in the Memory Bank.

### ✅ Good Behavior (Orchestrator)
Before distributing tasks, reads the Memory Bank, summarizes context, and ensures each subtask aligns with goals in `projectbrief.md` and constraints in `techContext.md`.

### ❌ Bad Behavior (Orchestrator)
Immediately assigns subtasks without consulting the Memory Bank, leading to duplicated work, missed dependencies, and no updates to `activeContext.md` or `progress.md` after task completion.
