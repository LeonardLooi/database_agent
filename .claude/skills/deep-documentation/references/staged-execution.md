# Staged Execution Reference

Loaded only when: heavy target detected, `--staged` flag present, or progress file found at Step -1.

---

## --staged Flag Detection

Detect staging intent from the user's message. Any of the following triggers staged mode:

| Pattern | Example |
|---------|---------|
| Explicit flag | `document src/auth/ --staged` |
| Natural language | `document the auth folder in stages` |
| Keyword | `staged documentation for ...` / `staged mode` |

Set `STAGED=true` when any pattern matches. Auto-detect (file count) sets it independently.

---

## Stage Sizing Rules

### File target
Never staged. Always single-pass. Return immediately to SKILL.md Step 1.

### Folder target

Split immediate source files into batches of 4, alphabetically ordered.
Add 1 final synthesis stage always.

```
Files: [a.py, b.py, c.py, d.py, e.py, f.py, g.py, h.py, i.py]  (9 files)

Stage 1: [a.py, b.py, c.py, d.py]  → Sections 1–7 for these files
Stage 2: [e.py, f.py, g.py, h.py]  → Sections 1–7 for these files
Stage 3: [i.py]                     → Sections 1–7 for this file
Stage 4: SYNTHESIS                  → Section 8 (10-lens bug analysis, reads .md only)
```

**Batch size guard:** Before reading each batch, run `wc -l` on each file.
If ANY file in the batch exceeds 300 lines → reduce batch to 2 files for that stage only.
Split the remaining files into a new stage. Do not re-number existing stages — append new stage.

```bash
# Count lines per file
wc -l {file1} {file2} {file3} {file4}

# If any > 300:
# Stage N:   [file1, file2]   (reduced batch)
# Stage N+1: [file3, file4]   (new stage, inserted)
```

### Feature target

Split by architectural layer. Each layer = 1 stage, regardless of file count per layer.
Add 1 final synthesis stage always.

```
Call chain: Controller → Service → Repository → External API client → Shared utilities

Stage 1: Controller layer    (all controller/route files)
Stage 2: Service layer       (all service/use-case files)
Stage 3: Repository layer    (all repository/DAO files)
Stage 4: External clients    (API clients, queue producers, cache adapters)
Stage 5: Shared utilities    (shared types, helpers used by this feature)
Stage 6: SYNTHESIS           (Section 8, reads .md only)
```

If a layer has > 6 files, apply the 4-file batch rule within that layer stage,
creating sub-stages: Stage 2a, Stage 2b, etc. Update the stage plan accordingly.

**Batch size guard applies within each layer stage identically to folder rules.**

---

## Progress File Schema

File name: `.deepdoc-progress-{output_filename_without_extension}.json`
Location: same directory as the output `.md` file (co-located with output, not source).

```json
{
  "skill": "deep-documentation",
  "version": 1,
  "target_type": "folder | feature | file",
  "target_path": "/absolute/path/to/source",
  "output_path": "/absolute/path/to/output.md",
  "output_mode": "co-located | centralized",
  "stack": "python | nestjs | java | flutter | angular",
  "template": "folder | feature | file",
  "staged_trigger": "auto | flag",
  "status": "in_progress | complete",
  "created": "2026-05-03T10:00:00Z",
  "last_updated": "2026-05-03T10:15:00Z",
  "resume_instruction": "Resume deep-documentation for {target_type} at {target_path}. Output: {output_path}. Stack: {stack}. Next pending stage: {N} — {description}.",
  "stages": [
    {
      "id": 1,
      "description": "Files a.py, b.py, c.py, d.py",
      "files": ["/abs/path/a.py", "/abs/path/b.py", "/abs/path/c.py", "/abs/path/d.py"],
      "status": "complete | in_progress | pending | skipped",
      "attempts": 1,
      "max_attempts": 2,
      "skip_reason": null
    }
  ]
}
```

**Field rules:**
- `resume_instruction` — must be fully self-describing. A fresh Claude session with no prior context must be able to resume from this field alone.
- `files` — absolute paths only. Relative paths break cross-session resume.
- `status` per stage — exactly one of: `complete`, `in_progress`, `pending`, `skipped`.
- `attempts` — incremented each time a stage is attempted (not just on failure).
- `skip_reason` — set when `status == "skipped"`. Human-readable reason string.

---

## Progress File Write Pattern

### Primary: Python one-liner (available on all modern systems)

```bash
python3 -c "
import json, sys
data = {
    'skill': 'deep-documentation',
    'version': 1,
    'target_type': '${TARGET_TYPE}',
    'target_path': '${TARGET_PATH}',
    'output_path': '${OUTPUT_PATH}',
    'output_mode': '${OUTPUT_MODE}',
    'stack': '${STACK}',
    'template': '${TEMPLATE}',
    'staged_trigger': '${STAGED_TRIGGER}',
    'status': 'in_progress',
    'created': '${ISO8601}',
    'last_updated': '${ISO8601}',
    'resume_instruction': 'Resume deep-documentation for ${TARGET_TYPE} at ${TARGET_PATH}. Output: ${OUTPUT_PATH}. Stack: ${STACK}. Next pending stage: 1.',
    'stages': ${STAGES_JSON}
}
with open('${PROGRESS_FILE_PATH}', 'w') as f:
    json.dump(data, f, indent=2)
"
```

### Fallback: Bash heredoc (use if Python unavailable)

```bash
cat > "${PROGRESS_FILE_PATH}" << 'PROGRESS_EOF'
{
  "skill": "deep-documentation",
  "version": 1,
  "target_type": "REPLACE_TARGET_TYPE",
  "target_path": "REPLACE_TARGET_PATH",
  "output_path": "REPLACE_OUTPUT_PATH",
  "status": "in_progress",
  "resume_instruction": "REPLACE_RESUME_INSTRUCTION",
  "stages": REPLACE_STAGES_JSON
}
PROGRESS_EOF
```

Note: Bash heredoc does not interpolate variables inside single-quoted `'HEREDOC'` delimiters.
Replace `REPLACE_*` placeholders manually in the string before writing.

### Stage update pattern (after each stage completes)

```bash
python3 -c "
import json
with open('${PROGRESS_FILE_PATH}', 'r') as f:
    data = json.load(f)
data['last_updated'] = '${ISO8601}'
for stage in data['stages']:
    if stage['id'] == ${STAGE_ID}:
        stage['status'] = 'complete'
        stage['attempts'] = ${ATTEMPTS}
        break
with open('${PROGRESS_FILE_PATH}', 'w') as f:
    json.dump(data, f, indent=2)
"
```

### Completion update pattern

```bash
python3 -c "
import json
with open('${PROGRESS_FILE_PATH}', 'r') as f:
    data = json.load(f)
data['status'] = 'complete'
data['last_updated'] = '${ISO8601}'
with open('${PROGRESS_FILE_PATH}', 'w') as f:
    json.dump(data, f, indent=2)
"
# Then delete:
rm "${PROGRESS_FILE_PATH}"
```

---

## .md Fallback Marker Format

Used when JSON write fails. Written as the FIRST line of the output .md:

```
<!-- deepdoc-fallback-progress: stage=0 status=in_progress target={absolute_target_path} output={absolute_output_path} -->
```

On resume detection (Step -1): scan line 1 of any `.md` in the output directory for this marker.
If found: treat as in_progress at stage 0, rebuild stage plan from scratch (re-detect target, re-count files).

---

## Stage Boundary Markers

Written to the output `.md` via Bash append (`>>`). Never use Write/Edit tools for appending — always use `>>` to avoid overwriting existing content.

```bash
# Stage start (written BEFORE generating content)
echo "" >> "${OUTPUT_PATH}"
echo "<!-- stage-start: ${STAGE_ID} | ${STAGE_DESCRIPTION} -->" >> "${OUTPUT_PATH}"

# Stage end (written AFTER all content for this stage is appended)
echo "<!-- stage-end: ${STAGE_ID} -->" >> "${OUTPUT_PATH}"
```

**Orphan detection on resume (Step -1):**

```bash
# Find stage-start without matching stage-end
LAST_START=$(grep -n "stage-start:" "${OUTPUT_PATH}" | tail -1 | cut -d: -f1)
LAST_END=$(grep -n "stage-end:" "${OUTPUT_PATH}" | tail -1 | cut -d: -f1)

if [ -n "$LAST_START" ] && { [ -z "$LAST_END" ] || [ "$LAST_START" -gt "$LAST_END" ]; }; then
  # Orphaned stage found — truncate from LAST_START to EOF
  head -n $((LAST_START - 1)) "${OUTPUT_PATH}" > "${OUTPUT_PATH}.tmp"
  mv "${OUTPUT_PATH}.tmp" "${OUTPUT_PATH}"
  # Reset that stage to pending in the progress file
fi
```

---

## Resume Algorithm

```
Step -1 fires → progress file found and valid:

1. Read stages[] from progress file
2. Find first stage where status == "pending" or status == "in_progress"
   → This is stage N
3. If stage N has attempts >= max_attempts (2):
   → Mark as "skipped", move to N+1
4. Increment stage N attempts by 1 in progress file
5. Print resume summary:
   "📋 Resuming deep-documentation: {target_type} at {target_path}
    Completed: stages {1..N-1} of {M} | Next: stage {N} ({description})
    Output: {output_path}"
6. Jump to Step 4c with stage N as the current stage
7. Continue loop for N+1, N+2, ... until all stages complete
8. Run Step 4d (synthesis) then Step 4e (cleanup) then Step 5
```

---

## Skipped Stage Reporting

When all stages complete (including any skipped), report skipped stages before Step 5:

```
⚠️  Skipped stages (manual review required):
    Stage 2 — {description}: {skip_reason}
    Stage 4 — {description}: {skip_reason}

These sections are absent from the output .md. Add them manually or re-run
with the problematic files resolved.
```
