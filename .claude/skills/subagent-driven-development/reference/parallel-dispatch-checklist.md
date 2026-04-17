# Parallel Dispatch — Independence Check

Use this checklist BEFORE dispatching any agents in parallel and AFTER they complete.

---

## Decision Tree — Can These Run in Parallel?

```
Multiple tasks to dispatch?
    |
    +-- Are they INDEPENDENT?
    |   (Independent = no shared file edits, no task depends on another's output)
    |   NO -> Sequential only. Do NOT dispatch in parallel.
    |
    +-- Do they touch SHARED STATE?
    |   (Shared state = same file, same DB table, same config, same interface)
    |   YES -> Sequential only. Parallel dispatch will cause conflicts.
    |
    +-- PASS: safe to dispatch in parallel
```

---

## Pre-Dispatch Independence Checklist

Complete before dispatching any parallel agents:

```
PARALLEL DISPATCH CHECK
=======================
[ ] Each task edits isolated files (no overlap in file paths)
[ ] No task depends on the output of another task in this batch
[ ] Each agent has explicit scope constraints ("Do NOT change X")
[ ] Tasks operate in different problem domains (e.g., auth vs. payments)
[ ] No shared config file (settings.json, pubspec.yaml, pom.xml) mutated by >1 agent

If ANY box is unchecked -> make it sequential. Do not proceed with parallel dispatch.
```

---

## Post-Completion Conflict Check

Run after ALL parallel agents return:

```
CONFLICT DETECTION
==================
[ ] Run full test suite — verify all agents' changes coexist without failures
[ ] Review each agent's changed files for unexpected overlaps
[ ] Check imports — no agent introduced a breaking import in a shared module
[ ] Spot-check one agent's diff for side effects outside its stated scope

If conflicts found -> resolve before marking any task complete.
```

---

## Examples

**Safe to parallelize:**
- Agent A: Add `UserController` to `src/auth/`
- Agent B: Add `PaymentController` to `src/payments/`
- Agent C: Write tests for `src/shared/utils.ts` (read-only for the source, writes only to `test/`)

**NOT safe to parallelize:**
- Agent A and Agent B both edit `pubspec.yaml` (shared config)
- Agent A adds a new provider and Agent B adds a screen that imports that provider (ordering dependency)
- Two agents both modify `src/shared/constants.ts`

---

## Integration

This checklist applies in both SDD dispatch modes:
- **Subagent mode:** Check before dispatching parallel background agents (e.g., parallel reviewers)
- **Team mode:** Check before assigning concurrent tasks to multiple teammates via `TaskUpdate`

Note: The SDD pipeline itself (Implementer → Spec Reviewer → Quality Reviewer) is always sequential per task by design. This checklist applies when you consider running independent tasks from different plan items in parallel.
