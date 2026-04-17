# Blackbox Policy

At the end of any session where decisions were made, code was written,
or constraints were stated: append ONE entry to `blackbox/session-log.md`.

## Entry Format

```
## {ISO-8601-timestamp}
### Decisions
- [Key architectural or technical decision made]
### Constraints Stated by User
- [Any constraint the user explicitly gave — tech choice, scope limit, deadline]
### Files Modified
- [file path] — [one-line reason]
### Deferred
- [Anything explicitly deferred to a future session]
---
```

## Rules
- Append ONLY — never edit or delete existing entries
- Skip if session was purely conversational (no code, no decisions)
- Keep each entry under 20 lines — summarize, don't transcript
- NEVER load `blackbox/session-log.md` into context unless user explicitly asks
- On month boundary: rename `session-log.md` → `archive-YYYY-MM.md`, create fresh `session-log.md`

## Plan Mutation Events

When any step in a `docs/plans/` file is split, inserted, skipped, reordered, or abandoned:

1. Update the `## Mutations Log` table in the plan file (`docs/plans/TEMPLATE.md` format)
2. Append to `blackbox/session-log.md` under `### Decisions`:
   `- Plan mutation: [type] on Task N of docs/plans/YYYY-MM-DD-<feature>.md — [reason]`

This ensures plan history is auditable across sessions without loading the full plan into context.

## Diagram Update Trigger

Naming convention: `src/auth/` maps to `docs/diagrams/auth-flow.md` (folder name = diagram prefix).

**If files modified this session are covered by an existing diagram in `docs/diagrams/`:**
- Update that diagram before ending the session
- Note in Decisions: "Updated docs/diagrams/[name].md — [one-line reason]"

**If a new service, flow, or integration was built and no diagram exists yet:**
- Generate a Mermaid diagram of the new component
- Save to `docs/diagrams/[feature-name]-flow.md`
- Note in Decisions: "Created docs/diagrams/[name].md"

**If unsure whether a diagram needs updating:** check `docs/diagrams/` for files whose prefix matches the folders you modified.

## Exit Signal Detection

When the user sends any of these exit signals, immediately append a session log entry to
`blackbox/session-log.md` — do NOT wait for an explicit command:

```
"that's all for now"
"done for today"
"i'm heading out" / "heading out"
"going out" / "going out now"
"talk later" / "talk to you later"
"closing the window" / "closing this"
"wrapping up" / "let's wrap up"
"end of session"
"bye" / "goodbye" (when used as a session closer, not mid-conversation)
```

### Trigger Behavior

On exit signal detection:
1. Check `git diff --stat` — were any files changed this session?
2. If YES → immediately write the blackbox entry (format defined in Entry Format above)
3. If NO (conversation-only session) → skip the entry per the "Skip if conversational" rule above
4. Do NOT batch saves — write immediately on signal, not at session end

### Exit Signal ≠ Mid-Task Pause

Do NOT trigger on:
- "hold on" / "hmm" / "let me think" — user is pausing, not leaving
- "one more thing" — user is continuing
- "actually" — user is redirecting, not ending
