# Riverpod Review Checklist

## 1. Provider Type Selection

Verify correct provider types:
- [ ] `@riverpod` for computed/derived values
- [ ] `@Riverpod(keepAlive: true)` for app-lifetime state
- [ ] `AsyncNotifier` for async state with mutations
- [ ] `Notifier` for sync state with mutations
- [ ] `StreamNotifier` for real-time data
- [ ] Avoid raw `StateProvider` in new code

## 2. Ref Usage Patterns

Check:
- [ ] `ref.watch()` in `build()` for reactive updates
- [ ] `ref.read()` for one-time reads (callbacks, events)
- [ ] `ref.listen()` for side effects
- [ ] `ref.invalidate()` for manual refresh
- [ ] No `ref.watch()` in event handlers

## 3. AsyncValue Handling

Verify:
- [ ] Always handle loading, error, and data states
- [ ] Use `AsyncValue.when()` for exhaustive matching
- [ ] Provide meaningful loading indicators
- [ ] Display user-friendly error messages
- [ ] Consider `AsyncValue.guard()` for error handling

## 4. Provider Lifecycle

Check:
- [ ] AutoDispose for screen-scoped state
- [ ] `keepAlive: true` only when necessary
- [ ] Proper family parameters for parameterized providers
- [ ] No providers created inside widgets
- [ ] Dispose of resources in `ref.onDispose()`

## 5. State Mutations

Review:
- [ ] Mutations through notifier methods, not direct state changes
- [ ] Optimistic updates with rollback
- [ ] Loading states during mutations
- [ ] Error handling for failed mutations

## 6. Code Generation

Verify:
- [ ] Using `@riverpod` annotation (not manual providers)
- [ ] Build runner generates `.g.dart` files
- [ ] Part directives present for generated code
- [ ] Notifier classes extend generated base classes

## Common Anti-Patterns

1. **watch() in Callbacks** — Using ref.watch inside button onPressed
2. **Missing AsyncValue Handling** — Not handling loading/error states
3. **Provider in Widget** — Creating providers inside build methods
4. **Wrong Provider Type** — Using StateProvider when Notifier needed
5. **Missing keepAlive** — App-level state disposed unexpectedly
6. **Over-watching** — Watching entire state when select would suffice
7. **Circular Dependencies** — Providers watching each other
8. **Missing Dispose** — Resources not cleaned up on dispose

## Output Format

For each finding:

```markdown
### [Riverpod Issue Title]

**Severity:** P1 CRITICAL / P2 IMPORTANT / P3 IMPROVEMENT
**Category:** Provider Type / Ref Usage / AsyncValue / Lifecycle / Mutation
**Location:** `file_path:line_number`

**Issue:**
[Description of the Riverpod pattern issue]

**Problem:**
[What goes wrong with current approach]

**Solution:**
[Correct Riverpod pattern to use]

**Before:**
```dart
// Incorrect pattern
```

**After:**
```dart
// Correct Riverpod pattern
```
```

## Severity Levels

- P1: Riverpod misuse causing bugs or crashes
- P2: Patterns that will cause issues at scale
- P3: Best practice improvements
