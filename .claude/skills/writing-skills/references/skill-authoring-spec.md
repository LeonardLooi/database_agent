# Skill Authoring Spec (Condensed)

## Source

Condensed from the official Anthropic skill authoring specification. Used by the `writing-skills` skill as the authoritative reference for skill creation rules.

## The Core Principle: Context is a Public Good

Every token loaded into Claude's context window costs real money and occupies finite space. Skill authors must treat context as a shared resource:

- **Concise is key** -- write skills that are dense with value, not dense with words
- **Progressive disclosure** -- load only what's needed, when it's needed
- **Degrees of freedom** -- give Claude enough guidance to work, not a rigid script

## Frontmatter Spec

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Matches directory name; used for identification |
| `description` | string | Primary trigger text; determines when Claude loads this skill |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `allowed-tools` | string | Comma-separated tool list; limits available tools |
| `metadata` | map | Arbitrary key-value metadata |

**Important:** The `allowed-tools` field IS valid per this spec. Some older skill samples incorrectly omit it -- always include it in new skills.

## What Makes a Good Description

The description field is the skill's search engine optimization (CSO -- Claude Search Optimization).

```
GOOD description includes:
+ Explicit "Use when..." or "Triggers when..." phrasing
+ The technology names (e.g., "Flutter", "NestJS", "Spring Boot")
+ The action words (e.g., "building", "reviewing", "debugging", "testing")
+ Synonyms for the same concept (e.g., "test", "spec", "unit test", "TDD")

BAD description:
- Too short: "Flutter skill" -- no trigger words
- Too vague: "Use for mobile development" -- doesn't match specific queries
- Missing synonyms: Only mentions "testing" but not "TDD" or "test-driven"
```

## What NOT to Include in a Skill Directory

| File | Why Not |
|------|---------|
| `README.md` | Skills are not packages -- no user installation needed |
| `INSTALLATION_GUIDE.md` | Same reason |
| `CHANGELOG.md` | Version history belongs in git commit history |
| `CONTRIBUTING.md` | Meta-meta documentation; no developer reads it |
| `requirements.txt` / `package.json` | Skills don't have dependencies |

## The Iron Law Pattern

Every effective skill leads with an Iron Law -- a short, memorable rule that captures the most important constraint:

```markdown
## Iron Law

**NO <ACTION> WITHOUT <PREREQUISITE> FIRST**
```

Examples from this codebase:
- `systematic-debugging`: "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST"
- `verification-before-completion`: "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"
- `writing-skills`: "NO SKILL AUTHORING WITHOUT READING AN EXISTING SKILL FIRST"

The Iron Law appears first in the body, before any other content.

## Decision Trees over Prose

Prefer decision trees to paragraphs:

```
# BAD -- prose
When you need to add code, first check if a relevant file exists.
If it does, modify that file. If not, consider whether the code
is more than 150-200 lines of cohesive logic, and if so, create
a new file. Otherwise, find the closest existing file.

# GOOD -- decision tree
Need to add code?
    |
    v
Does relevant file exist?
    YES -> Modify existing file (DEFAULT)
    NO  -> Is this >150 lines of cohesive new logic?
               YES -> Create new file (ask human first)
               NO  -> Add to closest existing file
```

## Cross-Reference Pattern

When a skill overlaps with another, use explicit cross-references instead of duplicating content:

```markdown
> For [specific scenario], see `<other-skill-name>` -- [one sentence on what it adds].
```

Never copy-paste content from one skill into another. Reference it.

## Checklist for Reviewing a Skill You've Written

```
[] Iron Law appears first?
[] Description includes all trigger words?
[] allowed-tools listed and minimal?
[] Body <=500 lines?
[] Deep content in references/, not inline?
[] No README.md / CHANGELOG.md in directory?
[] Cross-references use "see X" pattern, no duplicate content?
[] Decision trees where prose would be verbose?
```
