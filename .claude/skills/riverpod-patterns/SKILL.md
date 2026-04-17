---
name: riverpod-patterns
description: "This skill provides Riverpod state management patterns and best practices for Flutter applications. Use when reviewing or writing Riverpod providers, AsyncValue handling, ref usage, or provider lifecycle management."
allowed-tools: Read
metadata:
  triggers: Riverpod, Flutter state management, Riverpod provider, AsyncValue, StateNotifier, ConsumerWidget, AsyncNotifier
  related-skills: flutter-mobile, ui-standards-tokens
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

**Iron Law:** Always use the correct Riverpod provider type for the use case; never use StateProvider for async data or FutureProvider for mutable state.

# Riverpod Patterns

Correct Riverpod patterns for Flutter state management with code_generation style.

**When to use:** Writing or reviewing Riverpod providers, AsyncNotifier, AsyncValue.when, ref.watch vs ref.read, family providers, or provider lifecycle.

**Process:**

1. **Identify pattern needed** from user request
2. **Load reference:** Read `reference/riverpod-core-patterns.md` for code examples and rules
3. **Apply patterns** using loaded reference
4. **Verify:** Confirm ref.watch is only in build(), ref.read only in callbacks, all AsyncValue states handled visibly

## Quick Reference — Most Common Patterns

### Provider Type Selection

```dart
// ✅ Read-only async data (API call, DB read)
@riverpod
Future<List<User>> userList(UserListRef ref) async {
  return ref.watch(userRepositoryProvider).getAll();
}

// ✅ Mutable state with async operations
@riverpod
class UserNotifier extends _$UserNotifier {
  @override
  Future<User> build(String userId) async {
    return ref.watch(userRepositoryProvider).getById(userId);
  }

  Future<void> update(UserUpdateDto dto) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() =>
      ref.read(userRepositoryProvider).update(dto));
  }
}

// ❌ WRONG — never use StateProvider for async data
final userProvider = StateProvider<User?>((ref) => null); // no async support
```

### AsyncValue.when — All 3 states required

```dart
// ✅ All 3 states handled visibly
ref.watch(userListProvider).when(
  data: (users) => UserListWidget(users: users),
  loading: () => const CircularProgressIndicator(),
  error: (err, stack) => ErrorWidget(message: err.toString()), // never swallow
);

// ❌ WRONG — skipLoadingOnReload hides loading state from user
ref.watch(userListProvider).when(
  skipLoadingOnReload: true, // only acceptable after explicit UX decision
  data: (users) => UserListWidget(users: users),
  loading: () => const SizedBox.shrink(), // invisible loading = silent failure
  error: (err, stack) => const SizedBox.shrink(), // swallowed error
);
```

### ref.watch vs ref.read

```dart
// ✅ ref.watch — only inside build()
@override
Widget build(BuildContext context, WidgetRef ref) {
  final users = ref.watch(userListProvider); // rebuilds on change
  return UserListWidget(users: users.valueOrNull ?? []);
}

// ✅ ref.read — only inside callbacks/event handlers
void onButtonPressed(WidgetRef ref) {
  ref.read(userNotifierProvider.notifier).refresh(); // one-time action
}

// ❌ WRONG — ref.watch in a callback (causes infinite rebuild)
onPressed: () => ref.watch(userNotifierProvider.notifier).refresh(),
```

## Reference Files

| File | Contents | Load When |
|------|----------|-----------|
| `reference/riverpod-core-patterns.md` | Code examples, provider types, ref usage rules | Writing providers, ref.watch/read, AsyncValue handling |
| `reference/riverpod-review-checklist.md` | Review checklist for Riverpod code audits (used by `riverpod-reviewer` agent) | Reviewing Riverpod code, running riverpod-reviewer agent |

## Error Handling

**Provider not found**: Ensure `ProviderScope` wraps the widget tree. Check that generated `.g.dart` files are up to date (`dart run build_runner build`).

**AsyncValue stuck loading**: Verify the repository method returns data. Use `AsyncValue.guard()` to catch and surface errors instead of silent failures.
