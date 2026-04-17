# GenUI Conversation Orchestration

## Overview

The `Conversation` class is the orchestration engine of GenUI. It manages the conversation history, sends user input to the AI model, receives structured responses, and drives the UI generation loop. It connects the `Catalog` (what widgets are available) to the `Transport` (how messages flow) to the `SurfaceController` (how UI is rendered).

## Conversation Lifecycle

```
1. Initialize Conversation with Catalog + Transport + Model config
    |
2. User sends message (text or voice transcription)
    |
3. Conversation adds user message to history
    |
4. Conversation invokes the model via Transport adapter
    |
5. Model streams A2UI messages (surfaceUpdate, dataModelUpdate, beginRendering)
    |
6. SurfaceController processes each message, updates surface state
    |
7. Flutter widgets rebuild reactively from surface state
    |
8. User interacts with rendered widget (click, select, type)
    |
9. Interaction sent back as userAction to Conversation
    |
10. Conversation sends userAction to model -> back to step 5
```

## Setting Up a Conversation

```dart
import 'package:genui/genui.dart';
import 'package:genui_a2a/genui_a2a.dart';

class TriageConversationManager {
  late final Conversation _conversation;
  late final SurfaceController _surfaceController;

  Future<void> initialize({
    required Catalog catalog,
    required String triageEndpoint,
  }) async {
    // 1. Create the transport adapter (connects to your ADK backend)
    final transport = A2uiTransportAdapter(
      endpoint: triageEndpoint,
      // SSE streaming from the triage agent
      streamMode: StreamMode.sse,
    );

    // 2. Create the surface controller (manages rendered surfaces)
    _surfaceController = SurfaceController();

    // 3. Create the conversation
    _conversation = Conversation(
      catalog: catalog,
      transport: transport,
      surfaceController: _surfaceController,
      systemPrompt: _triageSystemPrompt,
    );
  }

  /// Send a user message and get AI response
  Future<void> sendMessage(String text) async {
    await _conversation.sendMessage(text);
    // SurfaceController is automatically updated with new surfaces
  }

  /// Send a user action (widget interaction) back to the model
  Future<void> sendAction(UserAction action) async {
    await _conversation.sendAction(action);
  }

  /// Get the current surface state for rendering
  SurfaceController get surfaceController => _surfaceController;

  /// Dispose when done
  void dispose() {
    _conversation.dispose();
  }
}
```

## PropertyHarbor Triage Conversation

For the PropertyHarbor triage flow, the Conversation connects to the ADK triage agent via SSE:

```dart
// triage_conversation.dart

import 'package:genui/genui.dart';
import 'widget_catalog.dart';

const _triageSystemPrompt = '''
You are a maintenance triage assistant for PropertyHarbor.
Your job is to collect information about a tenant's maintenance issue
using the available widget catalog.

Rules:
- Ask one question at a time using the most appropriate widget type
- Start with issue description, then narrow down with follow-up widgets
- Use photo_upload when visual evidence would help
- Use dropdown for multiple-choice questions (2-6 options)
- Use free_text for open-ended details
- Use rating for severity/urgency assessment
- Use confirmation for yes/no questions
- After collecting enough information, provide a summary and category
''';

/// Creates and configures the triage conversation for a tenant.
///
/// [jobId] — The triage job ID from `POST /triage/start`
/// [baseUrl] — API base URL for the triage agent
Future<TriageConversationManager> createTriageConversation({
  required String jobId,
  required String baseUrl,
}) async {
  final manager = TriageConversationManager();
  await manager.initialize(
    catalog: buildTriageCatalog(),
    triageEndpoint: '$baseUrl/triage/$jobId/stream',
  );
  return manager;
}
```

## Conversation with Riverpod (PropertyHarbor Pattern)

Since PropertyHarbor uses Riverpod 3.x for state management:

```dart
// triage_conversation_provider.dart

import 'package:riverpod/riverpod.dart';
import 'package:shared_ui/widgets/gen_ui/triage_conversation.dart';

/// Provider for the triage conversation manager.
/// Scoped to the triage screen lifecycle.
final triageConversationProvider = AsyncNotifierProvider.autoDispose<
    TriageConversationNotifier, TriageConversationManager>(
  TriageConversationNotifier.new,
);

class TriageConversationNotifier
    extends AutoDisposeAsyncNotifier<TriageConversationManager> {
  @override
  Future<TriageConversationManager> build() async {
    final jobId = ref.watch(triageJobIdProvider);
    final apiConfig = ref.watch(apiConfigProvider);

    final manager = await createTriageConversation(
      jobId: jobId,
      baseUrl: apiConfig.baseUrl,
    );

    // Auto-dispose when provider is disposed
    ref.onDispose(() => manager.dispose());

    return manager;
  }
}
```

## Message History

The `Conversation` maintains a history of all messages exchanged. This history is:
- Sent to the model with each new request (for context)
- Available for display in a chat-style UI
- Automatically managed (no manual tracking needed)

```dart
// Access conversation history
final history = conversation.messages;
// Each message has:
//   - role: 'user' | 'assistant'
//   - content: text content
//   - surfaces: list of rendered surfaces (for assistant messages)
//   - timestamp: when the message was sent/received
```

## Streaming vs Non-Streaming

| Mode | Use Case | Transport Config |
|------|----------|-----------------|
| **SSE (streaming)** | Real-time triage — widgets appear as agent generates them | `StreamMode.sse` |
| **REST (non-streaming)** | Simple Q&A — full response at once | `StreamMode.rest` |
| **WebSocket** | Bidirectional real-time — both directions stream | `StreamMode.websocket` |

PropertyHarbor uses **SSE** for the triage flow because:
- Agent streams follow-up questions one at a time
- UI updates progressively as each widget arrives
- SSE auto-reconnects on connection drop
- Simpler than WebSocket for one-directional streaming

## Error Handling in Conversation

```dart
try {
  await conversation.sendMessage(userInput);
} on TransportException catch (e) {
  // Connection error — show retry option
  logger.error('Triage transport failed', error: e);
  // Fall back to static form (PropertyHarbor constraint §12)
  _showStaticFallbackForm();
} on CatalogValidationException catch (e) {
  // Agent sent invalid widget type — log and continue
  logger.warning('Invalid catalog type from agent', error: e);
  // Remaining valid widgets will still render
} on ConversationException catch (e) {
  // General conversation error
  logger.error('Conversation error', error: e);
  _showErrorState(e.message);
}
```

## Fallback: Static Form (PropertyHarbor Constraint §12)

Every AI flow must have a fallback. If GenUI fails:

```dart
/// Checks if GenUI conversation is healthy, falls back to static form if not.
Widget buildTriageWidget(TriageConversationManager? manager) {
  if (manager == null || manager.hasError) {
    // Fallback: static form fields
    // Ticket will have needs_classification = true
    return const StaticTriageForm();
  }
  return GenUITriageView(manager: manager);
}
```
