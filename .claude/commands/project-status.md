---
description: Get a quick status summary of the current project — files, structure, dependencies, and health
allowed-tools: Bash, Read, Glob, Grep
---

# Project Status Report

Analyze the current project and provide a concise status report:

1. **Project type detection** — identify if this is a Spring Boot, Angular, Flutter, or multi-project repo
2. **File counts** — total files, lines of code by language
3. **Directory structure** — show top 2 levels
4. **Dependencies** — list key dependencies from `pom.xml`, `package.json`, or `pubspec.yaml`
5. **Configuration health** — check if CLAUDE.md, .mcp.json, and `.claude/` are present
6. **Recent git activity** — last 5 commits (if git repo)
7. **Potential issues** — flag missing tests, TODO comments, or config problems

Output as a clean markdown summary.
