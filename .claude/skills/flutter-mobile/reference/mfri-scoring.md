# Mobile Feasibility & Risk Index (MFRI)

Use this scoring template BEFORE implementing any Flutter feature to quantify implementation risk.
A score below 3 is a hard stop — redesign before writing code.

---

## Scoring Formula

```
MFRI = (Platform Clarity + Accessibility Readiness)
       - (Interaction Complexity + Performance Risk + Offline Dependence)

Range: -10 to +10
```

---

## Dimension Scores (each -2 to +2)

### Platform Clarity (+2 to -2)
How clearly is the target platform defined?

| Score | Condition |
|-------|-----------|
| +2 | Platform(s) explicitly stated (iOS, Android, or both) AND device type known |
| +1 | Platform stated but device type assumed |
|  0 | Platform inferred from context |
| -1 | Platform ambiguous (may need platform-specific divergence) |
| -2 | Platform unknown — must ask before proceeding |

### Accessibility Readiness (+2 to -2)
How accessible is the design intent?

| Score | Condition |
|-------|-----------|
| +2 | Semantics labels defined, touch targets >= 48dp, contrast verified |
| +1 | Standard widgets used, no custom painting or gestures |
|  0 | Mix of standard and custom widgets |
| -1 | Custom widgets without Semantics defined |
| -2 | Complex gestures, canvas-based UI, or motion-heavy without reduce-motion support |

### Interaction Complexity (+2 to -2, subtracted)
How complex are the user interactions?

| Score | Condition |
|-------|-----------|
| +2 | Complex: multi-step gestures, drag-and-drop, custom input, real-time collaboration |
| +1 | Moderate: multiple form steps, conditional flows, nested navigation |
|  0 | Standard: simple forms, navigation, list interaction |
| -1 | Low: display-only screens with minimal interaction |
| -2 | Minimal: static content, single action |

### Performance Risk (+2 to -2, subtracted)
How likely is this feature to cause frame drops or jank?

| Score | Condition |
|-------|-----------|
| +2 | High: long lists without virtualization, heavy animations, large image sets, expensive computations on main thread |
| +1 | Moderate: multiple animated widgets, medium list, image loading |
|  0 | Standard: typical Riverpod/stream-driven screen |
| -1 | Low: simple stateless or single-provider widget |
| -2 | Minimal: static layout, no async dependencies |

### Offline Dependence (+2 to -2, subtracted)
How much does this feature depend on offline support?

| Score | Condition |
|-------|-----------|
| +2 | Full offline: local storage, sync conflict resolution, background sync |
| +1 | Partial offline: cached reads, queued writes |
|  0 | Online with cache-on-read (e.g., Firestore snapshots) |
| -1 | Online-required with error state handled |
| -2 | Online-only, graceful error shown when offline |

---

## Interpretation

| MFRI Score | Risk Level | Action |
|------------|------------|--------|
| 6 to 10 | Safe | Proceed normally |
| 3 to 5 | Moderate | Add explicit validation step, review edge cases before shipping |
| 0 to 2 | Risky | Simplify architecture — reduce scope or defer complex dimensions |
| -1 to -10 | Dangerous | **STOP. Redesign required before any code is written.** |

---

## Mandatory Checkpoint (fill before writing any widget code)

```
MFRI CHECKPOINT
===============
Feature: [feature name]

Scores:
  Platform Clarity:        [+2 / +1 / 0 / -1 / -2]  → [reason]
  Accessibility Readiness: [+2 / +1 / 0 / -1 / -2]  → [reason]
  Interaction Complexity:  [+2 / +1 / 0 / -1 / -2]  → [reason]  (subtracted)
  Performance Risk:        [+2 / +1 / 0 / -1 / -2]  → [reason]  (subtracted)
  Offline Dependence:      [+2 / +1 / 0 / -1 / -2]  → [reason]  (subtracted)

MFRI = ([Platform] + [Accessibility]) - ([Interaction] + [Performance] + [Offline])
     = [calculated score]

Risk Level: [Safe | Moderate | Risky | Dangerous]
Action:     [Proceed | Add validation | Simplify | STOP - redesign]

If Risky or Dangerous — list what to simplify before proceeding:
- [ ] [dimension]: [specific change to reduce score]
```

---

## Common Score Patterns

**Typical CRUD screen** (list + detail + form): MFRI ~5-7 → Safe
- Platform Clarity: +2 (iOS + Android stated)
- Accessibility: +1 (standard widgets)
- Interaction: -1 (standard form)
- Performance: -1 (simple list)
- Offline: -1 (online with graceful error)

**Offline-first sync screen**: MFRI ~0-2 → Risky
- Platform Clarity: +2
- Accessibility: +1
- Interaction: -1 (standard)
- Performance: -1 (moderate)
- Offline: -2 (full offline required)
→ Simplify: cache-on-read only, defer conflict resolution

**Real-time canvas collaboration**: MFRI ~-4 → Dangerous
- Platform Clarity: +1
- Accessibility: -2 (canvas, no Semantics)
- Interaction: -2 (multi-user gestures)
- Performance: -2 (canvas redraws)
- Offline: -1 (partial)
→ STOP: define accessibility strategy, reduce to single-user first, prototype performance

---

## Integration

- Run this checkpoint in the flutter-mobile skill **Before Writing Any UI Code** section
- If MFRI < 3: stop and consult the developer before proceeding
- If MFRI 3-5: add a validation milestone before the feature is marked complete
- MFRI score goes in the task description or plan document for traceability
