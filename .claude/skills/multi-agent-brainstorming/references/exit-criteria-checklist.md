# Exit Criteria Checklist

Run this checklist before Phase 3 arbitration. All items must be true before the Arbiter issues a verdict.

---

## Pre-Arbitration Checklist

```
□ Phase 1 Complete
  □ Understanding Lock stated (goal, constraints, assumptions)
  □ Initial design documented
  □ Decision Log started

□ Phase 2 Complete
  □ Skeptic / Challenger invoked — all objections logged
  □ Constraint Guardian invoked — all objections logged
  □ User Advocate invoked — all objections logged
  □ Primary Designer responded to every objection
  □ Each response logged in Decision Log

□ Decision Log Complete
  □ All objections have a Resolution entry
  □ All rejected objections have a rationale
  □ Design summary reflects all revisions made during review
  □ Alternatives considered are documented

□ Ready for Arbitration
  □ No objections in "PENDING" state
  □ No unresolved contradictions between reviewer feedback
  □ Design is coherent after all revisions
```

---

## If a Checklist Item is NOT Met

Do NOT proceed to arbitration. Return to the appropriate phase:

| Failing item | Action |
|-------------|--------|
| A reviewer was not invoked | Return to Phase 2, invoke the missing reviewer |
| An objection has no response | Primary Designer must respond before proceeding |
| Decision Log incomplete | Update the log before proceeding |
| Design has unresolved contradictions | Primary Designer must resolve before Arbiter reviews |

---

## After Arbitration

If verdict is `APPROVED`:
→ Proceed to `plan-mode-review` to lock the plan before implementation

If verdict is `REVISE`:
→ Make the required changes
→ Re-invoke only the reviewer(s) whose objections drove the REVISE decision
→ Re-run arbitration

If verdict is `REJECT`:
→ Return to `/brainstorm` for a new design pass
→ Decision Log from this session is preserved as context for the next pass
