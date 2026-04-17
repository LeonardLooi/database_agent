---
name: asc-id-resolver
description: Resolve App Store Connect IDs (app IDs, build IDs, version IDs, group IDs, tester IDs, submission IDs) from human-friendly names using asc CLI commands. Use when commands require IDs, when you only know the app name or bundle ID, or when you need to look up build numbers, TestFlight group names, or tester emails. Triggers: "resolve ID", "find app ID", "get build ID", "asc ID", "bundle ID lookup", "group ID", "tester ID", "version ID".
allowed-tools: Bash, Read
metadata:
  triggers: resolve ID, find app ID, get build ID, asc ID, bundle ID lookup, group ID, tester ID, version ID, App Store Connect ID
  related-skills: asc-cli-usage, asc-release-flow, asc-testflight-orchestration, asc-submission-health
  domain: mobile-deployment
  role: specialist
  scope: deployment
  output-format: commands
last-reviewed: "2026-03-15"
---

# asc id resolver

## Iron Law

**NEVER PASS A HUMAN-READABLE NAME TO AN ASC COMMAND THAT REQUIRES AN ID — RESOLVE THE ID FIRST**

Use this skill to map names to IDs needed by other commands.

## App ID
- By bundle ID or name:
  - `asc apps list --bundle-id "com.example.app"`
  - `asc apps list --name "My App"`
- Fetch everything:
  - `asc apps --paginate`
- Set default:
  - `ASC_APP_ID=...`

## Build ID
- Latest build:
  - `asc builds latest --app "APP_ID" --version "1.2.3" --platform IOS`
- Recent builds:
  - `asc builds list --app "APP_ID" --sort -uploadedDate --limit 5`

## Version ID
- `asc versions list --app "APP_ID" --paginate`

## TestFlight IDs
- Groups:
  - `asc beta-groups list --app "APP_ID" --paginate`
- Testers:
  - `asc beta-testers list --app "APP_ID" --paginate`

## Pre-release version IDs
- `asc pre-release-versions list --app "APP_ID" --platform IOS --paginate`

## Review submission IDs
- `asc review submissions-list --app "APP_ID" --paginate`

## Output tips
- JSON is default; use `--pretty` for debug.
- For human viewing, use `--output table` or `--output markdown`.

## Guardrails
- Prefer `--paginate` on list commands to avoid missing IDs.
- Use `--sort` where available to make results deterministic.

## Documentation Sources

| Source | How to Access | Purpose |
|--------|--------------|---------|
| asc CLI help | `asc apps --help`, `asc builds --help` | Discover list/filter flags for each entity type |
| asc output formats | `--output json \| table \| markdown` | Machine-parseable ID extraction |
