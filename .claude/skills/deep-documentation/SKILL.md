---
name: deep-documentation
description: "Generates deep, structured .md documentation files at three granularities: per-file (or Angular component), per-folder, and per-feature. Covers data pipeline, data contract, data handling, dependencies, outputs, usage examples, and bug analysis. Auto-splits heavy workloads into stages, persists progress to disk, and resumes autonomously after context compaction or session restart. Use when asked to document a file, folder, component, or feature, or to update existing documentation."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
metadata:
  triggers: document file, document folder, document feature, document component, generate docs, update docs, per-file documentation, deep documentation, doc generate, create documentation, document in stages, staged documentation
  related-skills: documentation-generation, openapi-spec-generation, changelog-generator, architecture-decision-records
  domain: workflow
  role: specialist
  scope: design
  output-format: document
last-reviewed: "2026-05-03"
---

## Iron Law: NO DOCUMENTATION WITHOUT READING THE TARGET SOURCE FIRST

Read the source file(s) before writing a single section. Never generate from memory.

---

## Process

### Step -0A — Progress File Check (runs before everything else)

Load `references/staged-execution.md` ONLY IF a progress file is found OR a heavy target / --staged flag is detected (load lazily — do not load for light single-file targets).

Check for a progress file in the expected output directory:
`.deepdoc-progress-{output-filename}.json`

```
IF progress file found:
  1. Parse JSON — if parse fails → silently fall through to FRESH START (Step 0)
  2. Validate required fields: skill, target_path, output_path, stages[]
     If invalid → warn user, offer to discard and restart fresh
  3. Staleness check: verify target_path still exists on disk
     If gone → warn: "Progress file found but target no longer exists at {path}.
                      Discard and start fresh?" Wait for user confirmation.
  4. Scan output .md for orphaned stage markers:
     Look for <!-- stage-start: N --> without a matching <!-- stage-end: N -->
     If found → truncate .md from that stage-start to EOF, reset stage N to pending
  5. Print resume summary:
     "📋 Resuming deep-documentation: {target_type} at {target_path}
      Completed: stages {1..N-1} of {M} | Next: stage {N} ({description})
      Output: {output_path}"
  6. Jump directly to Step 4c (staged loop) — skip Steps 0–3

IF no progress file found:
  → Continue to Step 0B
```

---

### Step 0B — Detect Target Type, Output Location, and Workload Size

**Target type** (ask if not clear from context):

| Target | Description |
|--------|-------------|
| **File** | Single source file (`.py`, `.ts`, `.java`, `.dart`) OR Angular component folder |
| **Folder** | A directory — documents all immediate files and their relationships (one level deep) |
| **Feature** | A named user capability spanning ≥2 files or ≥1 folder — traced from entry point outward |

**Angular component detection:** if the path contains `.component.ts` or is a folder with a `.component.ts` file inside, treat the entire component folder as one unit. Generate a single `.md` covering `.ts`, `.html`, `.scss`, and `.spec.ts` together.

**Output location** (ask if not specified — default: co-located):

| Mode | File | Folder | Feature |
|------|------|--------|---------|
| **Co-located** | `{dir}/{filename-no-ext}.md` | `{folder}/README.md` | `{entry-point-folder}/{feature-name}.md` |
| **Centralized** | `docs/files/{relative-path}.md` | `docs/folders/{relative-path}.md` | `docs/features/{feature-name}.md` |

**Heavy-target detection (load `references/staged-execution.md` if triggered):**

```
--staged flag triggers:
  - User message contains "--staged", "in stages", or "staged mode"

Auto-detect triggers:
  - Folder target with > 8 immediate source files
  - Feature target with > 6 files in the call chain

File target: NEVER staged — always single-pass (skip to Step 1)

IF heavy OR --staged flag:
  → Build stage plan (see staged-execution.md § Stage Sizing Rules)
  → Write progress file: {output_dir}/.deepdoc-progress-{output_filename_no_ext}.json
  → IF JSON write fails: embed fallback marker as first line of output .md:
      <!-- deepdoc-fallback-progress: stage=0 status=in_progress target={target_path} -->
  → Skip to Step 4c (staged loop)

IF light target:
  → Continue to Step 1 (no staging, no progress file)
```

---

### Step 1 — Detect Stack

Check for: `pom.xml` (Java/Spring Boot), `package.json` (NestJS/Angular), `pyproject.toml` (Python/FastAPI), `pubspec.yaml` (Flutter/Dart).

If ambiguous (monorepo), detect from the target file's extension and imports.

---

### Step 2 — Load Template

| Target | Primary template | Always load |
|--------|-----------------|-------------|
| File / Angular component | `references/file-doc-template.md` | `references/docstring-patterns.md` |
| Folder | `references/folder-doc-template.md` | `references/docstring-patterns.md` |
| Feature | `references/feature-doc-template.md` | `references/docstring-patterns.md` |

Load `references/readme-templates.md` only when folder doc replaces or supplements a README.
Load `references/cicd-doc-pipeline.md` only when CI/CD automation is explicitly requested.

---

### Step 3 — Check for Existing Doc

```
IF .md exists AND first line contains:
  <!-- generated: ... | skill: deep-documentation ... -->
  → SMART UPDATE MODE (Step 4b)

IF .md exists WITHOUT the skill header:
  → ASK: "This .md was not generated by this skill. Overwrite fully, or leave unchanged?"
  → Overwrite confirmed → FRESH GENERATION MODE (Step 4a)
  → Leave → STOP

IF .md does not exist:
  → FRESH GENERATION MODE (Step 4a)
```

---

### Step 4a — Fresh Generation (light targets only)

1. Read all source files in full
2. For **feature** targets: read in call-chain order from entry point outward
3. Fill every section from the loaded template — write "N/A — [reason]" if not applicable
4. Write output file with timestamp header as the absolute first line:
   ```
   <!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: {file|folder|feature} -->
   ```
5. Proceed to Step 5

---

### Step 4b — Smart Update Mode (light targets only)

1. Read the existing `.md` in full
2. Read all current source files in full
3. For each section in the existing doc:
   - **Discrepancy found** → rewrite that section based on current code
   - **No code counterpart** (manually added section) → preserve as-is
   - **Uncertain** → preserve content AND append:
     `<!-- Review: code may have changed since last generation — verify manually -->`
4. Replace the timestamp header (first line only) with updated timestamp
5. Proceed to Step 5

---

### Step 4c — Staged Execution Loop (heavy targets)

Read `references/staged-execution.md` for stage sizing rules, batch size adjustment, and the progress file write pattern.

For each pending stage in the stage plan:

```
1. Write stage boundary start marker (append to .md):
   echo "<!-- stage-start: {N} | {description} -->" >> {output_path}

2. Determine batch size:
   - Count lines of each file in this batch: wc -l {file}
   - IF any file > 300 lines → reduce batch to 2 files for this stage
   - Read all source files in this batch in full

3. Generate documentation sections for this batch using the loaded template
   (sections covered by this stage only — see staged-execution.md § Stage Sizing Rules)

4. Append generated content to output .md:
   Use Bash >> (append operator) — do NOT overwrite existing content

5. Write stage boundary end marker:
   echo "<!-- stage-end: {N} -->" >> {output_path}

6. Update progress file:
   - Mark stage N status: "complete"
   - Update last_updated: {ISO8601-UTC}
   - Increment attempts if this was a retry

7. IF stage failed twice (attempts >= max_attempts):
   - Mark stage N status: "skipped"
   - Append note to .md: "<!-- stage-{N} skipped: {reason} -->"
   - Continue to stage N+1

8. AFTER CONTEXT COMPACTION (if it fires mid-loop):
   Immediately re-read the progress file at {output_dir}/.deepdoc-progress-{name}.json
   Print the resume summary and continue from the next pending stage.
   Do not wait for user input.
```

---

### Step 4d — Final Synthesis Stage

After all data stages complete:

```
1. Read the COMPLETE output .md in full — do NOT re-read source files
   (all information needed for cross-cutting analysis is already in the .md)

2. Write synthesis stage boundary start marker:
   echo "<!-- stage-start: SYNTHESIS | Cross-cutting bug analysis -->" >> {output_path}

3. Apply all 10 bug/improvement lenses to the full document:
   - Review the entire .md as a whole
   - Identify patterns that span multiple files/layers
   - Write Section 8 (Possible Bugs and Room for Improvement) once, covering the full target

4. Append Section 8 content to .md

5. Write synthesis stage end marker:
   echo "<!-- stage-end: SYNTHESIS -->" >> {output_path}

6. Update progress file: status = "complete", last_updated = {ISO8601-UTC}
```

---

### Step 4e — Cleanup

```
1. Delete the progress file:
   rm {output_dir}/.deepdoc-progress-{name}.json

2. Write final timestamp header as the absolute first line of the .md
   (insert, not append — this replaces any fallback marker if present):
   <!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: {file|folder|feature} | stages: {N} -->

3. Proceed to Step 5
```

---

### Step 5 — Self-Check (Mandatory — gated)

**Gate:** Run Step 5 ONLY when:
- No progress file exists (light target complete), OR
- Progress file status == "complete" (staged target complete)

If a progress file exists with status == "in_progress" → skip Step 5, continue the staged loop.

After writing or updating the doc, verify it contains all of:

```
Self-check:
[ ] Objective and description present
[ ] How to use the code present (with examples)
[ ] Data pipeline present
[ ] Data handling present
[ ] Data contract present (includes types, not just names)
[ ] Data dependencies present
[ ] Output present
[ ] Possible bugs and room for improvement (all 10 lenses applied)
[ ] Timestamp header present as the first line
```

If any item is unchecked → add the missing section before reporting done.

---

## Post-Compaction Behavior

**If context compaction fires during a staged run:**

1. Immediately re-read the progress file at:
   `{output_dir}/.deepdoc-progress-{output_filename_no_ext}.json`
2. Print the resume summary (Stage N of M, next pending stage)
3. Continue from the next pending stage — do not restart from stage 1
4. Do not wait for user input

The progress file is self-describing: it contains the full target path, output path, stack, template, and stage plan. A completely fresh context can resume correctly from the progress file alone.

---

## Version Control Note

Generated `.md` files should be committed to version control. They are living documentation reviewable in PRs, not build artifacts.

**Add to `.gitignore`:**
```
.deepdoc-progress-*.json
```
Progress files are transient run-state — never commit them.

---

## References

| File | Content | Load When |
|------|---------|-----------|
| `references/staged-execution.md` | Stage sizing rules, progress file schema, resume algorithm, JSON write patterns | Heavy target detected, --staged flag, or progress file found at Step -1 |
| `references/file-doc-template.md` | Per-file and Angular component doc template | Documenting a single file or Angular component |
| `references/folder-doc-template.md` | Per-folder doc template (one level deep) | Documenting a directory |
| `references/feature-doc-template.md` | Per-feature doc template (call-chain order) | Documenting a named user capability |
| `references/docstring-patterns.md` | Javadoc, JSDoc, Python Google-style, Dart `///` patterns | Writing the data contract section |
| `references/readme-templates.md` | Stack-specific README templates | Folder doc replaces or supplements a README |
| `references/cicd-doc-pipeline.md` | GitHub Actions auto-doc pipeline, Redocly, GitHub Pages | CI/CD automation requested |

---

## Error Handling

- **Target type unclear** → ask before proceeding; never guess
- **Stack not detected** → ask the user to specify
- **Source file is empty** → document as empty with a note; do not skip
- **Existing `.md` has no skill header** → ask before overwriting
- **Section has no applicable content** → write "N/A — [reason]"; never omit sections silently
- **Angular component missing `.html` or `.scss`** → note the missing files; document what exists
- **Progress file parse fails** → silently fall through to FRESH START (do not warn)
- **Progress file write fails** → embed fallback marker in .md first line; continue
- **Stage fails twice** → mark stage as skipped, log reason, continue to next stage
- **Target path gone on resume** → warn user, offer to discard progress file
- **Orphaned stage-start marker found** → truncate .md from that marker, re-run that stage
