# Flutter Use-Case Layer

Use cases are optional domain-layer classes that encapsulate a single business operation.

## When to Add a Use Case

Add a use case when ANY of these are true:

1. The same business operation is called from **2+ ViewModels** — extract to avoid duplication
2. The operation **orchestrates 2+ repositories** — keeps ViewModel thin
3. The operation has **non-trivial business rules** that belong in the domain layer, not the UI or data layer

## When NOT to Add a Use Case

Single repository call with no business logic → call the repository directly from the ViewModel.
Do not add use cases for simple CRUD operations. Unnecessary indirection is worse than the
problem it was meant to solve.

```
// ❌ Unnecessary use case — just wraps one repo call with no logic
class GetPropertyUseCase {
  Future<Property> execute(String id) => _repo.getProperty(id);
}

// ✅ Just call the repository from the ViewModel directly
final property = await ref.read(propertyRepositoryProvider).getProperty(id);
```

## File Location

```
lib/features/<feature>/domain/use_cases/<name>_use_case.dart
```

## Example — Orchestrating Two Repositories

`SubmitMaintenanceTicketUseCase` creates the ticket AND triggers vendor pre-matching in one
atomic domain operation. Neither ViewModel nor repository alone owns this logic.

```dart
// lib/features/tickets/domain/use_cases/submit_maintenance_ticket_use_case.dart

class SubmitMaintenanceTicketUseCase {
  final TicketRepository _ticketRepo;
  final VendorMatchingRepository _vendorRepo;

  const SubmitMaintenanceTicketUseCase({
    required TicketRepository ticketRepo,
    required VendorMatchingRepository vendorRepo,
  })  : _ticketRepo = ticketRepo,
        _vendorRepo = vendorRepo;

  Future<Result<Ticket>> execute(CreateTicketParams params) async {
    // Step 1 — create the ticket
    final ticketResult = await _ticketRepo.create(params);
    if (ticketResult case Failure(:final error)) return Failure(error);

    final ticket = (ticketResult as Success<Ticket>).value;

    // Step 2 — trigger pre-matching (non-blocking; failures don't fail the ticket)
    await _vendorRepo.triggerPreMatch(ticket.id, ticket.category);

    return Success(ticket);
  }
}
```

Register in DI via a Riverpod provider:

```dart
@riverpod
SubmitMaintenanceTicketUseCase submitMaintenanceTicket(Ref ref) =>
    SubmitMaintenanceTicketUseCase(
      ticketRepo: ref.watch(ticketRepositoryProvider),
      vendorRepo: ref.watch(vendorMatchingRepositoryProvider),
    );
```

ViewModel calls the use case, not the repositories directly:

```dart
Future<void> submit(CreateTicketParams params) async {
  state = const AsyncValue.loading();
  state = await AsyncValue.guard(
    () => ref.read(submitMaintenanceTicketProvider).execute(params).then(
          (r) => switch (r) {
            Success(:final value) => value,
            Failure(:final error) => throw error,
          },
        ),
  );
}
```

## Testing

Use cases get **unit tests with fake repositories** — no mocks needed, no widget tree required.

```dart
// test/features/tickets/domain/use_cases/submit_maintenance_ticket_use_case_test.dart

void main() {
  test('creates ticket and triggers pre-match', () async {
    final ticketRepo = FakeTicketRepository();
    final vendorRepo = FakeVendorMatchingRepository();
    final useCase = SubmitMaintenanceTicketUseCase(
      ticketRepo: ticketRepo,
      vendorRepo: vendorRepo,
    );

    final result = await useCase.execute(CreateTicketParams(
      propertyId: 'p1',
      category: TicketCategory.plumbing,
      description: 'Leaking pipe',
    ));

    expect(result, isA<Success<Ticket>>());
    expect(vendorRepo.preMatchTriggered, isTrue);
  });
}
```

Fake repositories implement the repository interface and store calls in-memory —
no `mocktail` or `mockito` required for use-case tests.
