---
description: Add a new feature end-to-end across backend API, Angular UI, and/or Flutter mobile
argument-hint: "[feature description]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Add Feature End-to-End

Add a complete feature across the stack:

**Feature description:** $ARGUMENTS

## Steps
1. **Analyze** what layers are needed (backend API? frontend UI? mobile screen? database?)
2. **Database** — create migration and update ERD if new entities are needed
3. **Backend API** — create DTO, entity, repository, service, controller, and test
4. **Angular UI** — create component, service, route, and test
5. **Flutter Mobile** — create model, provider, screen, and test
6. Only create the layers that are relevant to the feature request.

Use the appropriate agents and skills for each layer. Follow all conventions from CLAUDE.md.
