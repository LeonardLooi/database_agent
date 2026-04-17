---
description: Clean up merged, stale, and orphaned git branches. Protects main/develop/release/* automatically. Supports --dry-run (preview only), --force (no confirmation), --remote-only, --local-only. Run after a sprint ends or before a release.
allowed-tools: Bash, Read, Grep
---

# Branch Cleanup

Audit and clean up local and remote branches safely. Always categorises before deleting.

## Step 1 — Gather Repository State

```bash
echo "=== Current branch ==="
git branch --show-current

echo "=== All local branches (by last commit) ==="
git for-each-ref --sort=-committerdate refs/heads/ \
  --format='%(refname:short)  %(committerdate:relative)  %(authorname)'

echo "=== Merged into develop/main ==="
git branch --merged develop 2>/dev/null || git branch --merged main 2>/dev/null

echo "=== Remote tracking branches ==="
git branch -r
```

## Step 2 — Determine Mode

Check `$ARGUMENTS` for a mode flag:

| Flag | Behaviour |
|------|-----------|
| *(none)* | Interactive — confirm before each deletion |
| `--dry-run` | Show what would be deleted; make no changes |
| `--force` | Delete all merged branches without per-branch confirmation |
| `--remote-only` | Prune stale remote-tracking refs only; skip local branches |
| `--local-only` | Delete merged local branches only; skip remote prune |

## Step 3 — Protected Branches (NEVER delete)

Skip these regardless of mode or flags:

- `main`, `master`, `develop`, `staging`, `production`
- Any branch matching `release/*` or `hotfix/*`
- The currently checked-out branch
- Any branch with unpushed commits (`git log origin/<branch>..<branch>` returns commits)

## Step 4 — Categorise Branches

Classify every non-protected branch into one of:

1. **Safe to delete** — merged into develop/main, no unpushed commits
2. **Stale** — last commit > 30 days ago, not merged → list for human review, do NOT auto-delete
3. **Orphaned remote** — remote-tracking ref with no active PR → prune with `git remote prune origin`

## Step 5 — Execute Cleanup

```bash
# Always prune stale remote-tracking refs first (safe, no branch deleted)
git remote prune origin

# Get merged branches excluding protected patterns
git branch --merged develop 2>/dev/null | \
  grep -vE '^\*|\bmain\b|\bmaster\b|\bdevelop\b|\bstaging\b|\bproduction\b|release/|hotfix/'
```

Apply the mode from Step 2 to each merged branch found above:
- `--dry-run`: print `[DRY RUN] Would delete: <branch>` — no deletions
- `--force`: run `git branch -d <branch>` immediately for each
- Interactive: prompt `Delete merged branch '<branch>'? [y/N]` — delete only on `y`
- Stale (unmerged) branches: list them but never auto-delete regardless of mode

## Step 6 — Report

```
## Branch Cleanup Report

### Deleted (N branches)
- <branch> — merged N days ago

### Skipped — Protected
- develop, main

### Skipped — Stale, Unmerged (review manually)
- <branch> — last commit: X days ago, not in develop/main

### Remote tracking refs pruned: N

Run `git branch -a` to confirm final state.
```

$ARGUMENTS
