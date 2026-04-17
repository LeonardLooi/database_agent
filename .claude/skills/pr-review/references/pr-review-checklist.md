# PR Review Checklist

Use during Stage 1 analysis to structure your review.md findings.

## Blocking Issues (must fix before merge)

### Security
- [ ] No secrets, tokens, API keys, or credentials hardcoded
- [ ] Input validation present on all user-facing inputs
- [ ] Authorization checks present (not just authentication)
- [ ] No SQL injection, XSS, or SSRF vectors introduced
- [ ] New dependencies from trusted sources, not abandoned packages

### Correctness
- [ ] Logic handles error cases, not just the happy path
- [ ] No silent failures in catch/except blocks
- [ ] Async code handles rejection and timeout cases
- [ ] Null/undefined/None cases handled at system boundaries

### Breaking Changes
- [ ] API contracts backward-compatible, or migration path provided
- [ ] Database migrations reversible (has both up and down)
- [ ] No removal of public interfaces without deprecation notice
- [ ] Environment variable changes documented

## Important Issues (should fix before merge)

### Testing
- [ ] New logic has at least one test covering the happy path
- [ ] Error conditions have at least one test
- [ ] Existing tests pass (CI green)
- [ ] No tests deleted without clear explanation

### Code Quality
- [ ] No unused imports, variables, or dead code introduced
- [ ] No duplicate logic (DRY — check for similar implementations elsewhere)
- [ ] Error handling follows project conventions (logged, not swallowed)
- [ ] Matches project idioms — doesn't introduce a new paradigm mid-codebase

### Documentation
- [ ] Comments accurate vs implementation (not stale)
- [ ] Public API changes documented
- [ ] Complex logic has explanatory comments (not just what, but why)

## Suggestions (nice to have)

### Simplification
- [ ] Could any section be significantly shorter with same behavior?
- [ ] Any premature abstractions (factory/plugin for a single current use)?
- [ ] Any wrapper-around-wrapper patterns that add no value?

### Performance
- [ ] No N+1 query patterns introduced (check loops with DB calls)
- [ ] No unnecessary blocking calls in async contexts
- [ ] Large data sets use pagination or streaming, not full loads

### Type Safety
- [ ] Types express domain intent, not just data shape
- [ ] No `any` / `Object` / untyped maps used for domain concepts
- [ ] Invalid states unrepresentable where the type system allows it

## Decision Guide

| Finding | Decision |
|---------|---------|
| No blocking issues | APPROVE |
| Blocking issues exist | REQUEST CHANGES |
| Questions but no blockers | COMMENT (ask before deciding) |
| Minor suggestions only | APPROVE with suggestions noted |
| Uncertain about intent | COMMENT (ask for clarification first) |
