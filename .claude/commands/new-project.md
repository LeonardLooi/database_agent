---
description: Detect project type from natural language and route to the correct scaffold command. Say "new-project flutter fitness tracker" or "new-project python api" and it routes automatically.
argument-hint: "[project description, e.g. 'flutter todo app' or 'python api for invoices']"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# New Project — Keyword Router

**Request:** $ARGUMENTS

## Step 1 — Detect Project Type

Analyze `$ARGUMENTS` using this keyword matrix. Match the FIRST row that fits:

| Keywords in request | Project Type | Route to command |
|---------------------|--------------|-----------------|
| `flutter`, `dart`, `ios app`, `android app` | Flutter Mobile | `/scaffold-flutter-app` |
| `react native`, `expo`, `rn app` | React Native | Load `mobile-developer` skill |
| `nestjs`, `nest`, `node api`, `typescript api` | NestJS API | `/scaffold-nestjs-api` |
| `python`, `fastapi`, `django`, `flask` | Python API | `/scaffold-python-api` |
| `java`, `spring`, `spring boot` | Java Spring API | `/scaffold-spring-api` |
| `angular`, `spa`, `web app`, `dashboard` | Angular SPA | `/scaffold-angular-app` |
| `agent`, `langchain`, `langgraph`, `ai agent`, `rag` | Agentic AI | `/scaffold-agentic-ai` |
| `adk`, `gemini agent`, `google adk` | Google ADK Agent | `/scaffold-google-adk` |
| `a2ui`, `agent ui`, `agent-driven ui` | A2UI Angular | `/scaffold-a2ui` |
| `database`, `schema`, `postgres`, `sql` | Database Schema | `/design-database` |
| No clear match | Ambiguous | Ask one clarifying question (see Step 2) |

## Step 2 — If ambiguous

Ask exactly ONE question:
```
I need one clarification: what is the primary technology?
Options: Flutter mobile / NestJS API / Python FastAPI / Java Spring / Angular SPA / AI Agent
```

Do not ask multiple questions. One answer is enough to route.

## Step 3 — Route

Once type is determined:

1. **Extract the app name** from `$ARGUMENTS` (everything after the tech keyword, e.g. "fitness tracker" from "flutter fitness tracker"). Use as the project name for the scaffold command.

2. **Run the Plan Verification gate first:**
   ```
   🔴 Does docs/plans/YYYY-MM-DD-<project-name>.md exist?
   NO → Create it before scaffolding (list: feature scope, key screens/endpoints, data models)
   YES → Verify it is current, then proceed
   ```

3. **Execute the routed command** with the extracted name as argument.

## Step 4 — Flutter-specific additions

If routed to Flutter (`/scaffold-flutter-app`):
- Also load `mobile-design` skill and complete Mobile Checkpoint before writing any UI
- Run MFRI scoring (score must be ≥ 3 to proceed)
- After scaffold: load `flutter-mobile` skill for implementation patterns

## Examples

| User input | Detected type | Action |
|------------|--------------|--------|
| `new-project flutter fitness tracker` | Flutter Mobile | `/scaffold-flutter-app fitness-tracker` |
| `new-project python invoice api` | Python API | `/scaffold-python-api invoice-api` |
| `new-project nestjs user management` | NestJS API | `/scaffold-nestjs-api user-management` |
| `new-project angular admin dashboard` | Angular SPA | `/scaffold-angular-app admin-dashboard` |
| `new-project langgraph rag pipeline` | Agentic AI | `/scaffold-agentic-ai rag-pipeline` |
| `new-project java spring orders` | Java Spring | `/scaffold-spring-api orders` |
