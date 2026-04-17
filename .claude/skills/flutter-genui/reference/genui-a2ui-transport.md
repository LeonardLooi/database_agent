# GenUI A2UI Transport

## Overview

GenUI uses A2UI under the hood as its communication protocol. The `A2uiTransportAdapter` is the bridge between the Flutter client and the AI agent backend. It handles sending user messages, receiving streamed A2UI responses, and converting between the wire format and GenUI's internal types.

## A2UI Message Types (Quick Reference)

| Type | Direction | Purpose |
|------|-----------|---------|
| `surfaceUpdate` | agent -> client | Adds/updates UI components on a named surface |
| `dataModelUpdate` | agent -> client | Populates reactive state |
| `beginRendering` | agent -> client | Signals surface is ready to render |
| `deleteSurface` | agent -> client | Removes a surface |
| `userAction` | client -> agent | Reports user interaction |

For full protocol details, see `../a2ui-angular/reference/a2ui-protocol.md`.

## A2uiTransportAdapter

The `A2uiTransportAdapter` from the `genui_a2a` package connects GenUI to any A2UI-compatible backend.

```dart
import 'package:genui_a2a/genui_a2a.dart';

final transport = A2uiTransportAdapter(
  endpoint: 'https://api.propertyharbor.com/triage/$jobId/stream',
  streamMode: StreamMode.sse,
  headers: {
    'Authorization': 'Bearer $authToken',
    'Content-Type': 'application/json',
  },
);
```

## SSE Streaming (PropertyHarbor Pattern)

PropertyHarbor's triage agent streams responses via Server-Sent Events (SSE). Each SSE `data:` line contains one A2UI JSONL message.

### Wire Format

```
data: {"surfaceUpdate":{"surfaceId":"main","components":[...]}}

data: {"dataModelUpdate":{"surfaceId":"main","contents":[{"key":"category","valueString":"plumbing"}]}}

data: {"beginRendering":{"surfaceId":"main","root":"root"}}
```

### PropertyHarbor SSE Payload (Extended)

PropertyHarbor extends the standard A2UI payload with triage-specific fields:

```json
{
  "surfaceUpdate": {
    "surfaceId": "triage",
    "components": [
      {
        "id": "root",
        "component": {
          "type": "Column",
          "children": {"explicitList": ["question-text", "widget-1"]}
        }
      },
      {
        "id": "question-text",
        "component": {
          "type": "Text",
          "literalString": "Is the water dripping or flooding?",
          "usageHint": "body"
        }
      },
      {
        "id": "widget-1",
        "component": {
          "type": "dropdown",
          "label": {"literalString": "Severity"},
          "options": ["dripping", "flooding", "other"],
          "required": true
        }
      }
    ]
  }
}
```

### Custom SSE Transport (If genui_a2a Doesn't Fit)

If the `genui_a2a` package doesn't match your backend's SSE format, implement a custom transport:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Custom SSE transport for PropertyHarbor triage agent.
class TriageTransport {
  final String endpoint;
  final Map<String, String> headers;

  TriageTransport({required this.endpoint, required this.headers});

  /// Streams A2UI messages from the triage agent SSE endpoint.
  Stream<A2uiMessage> streamTriage(String userMessage) async* {
    final client = http.Client();
    try {
      final request = http.Request('GET', Uri.parse(
        '$endpoint?message=${Uri.encodeComponent(userMessage)}',
      ));
      request.headers.addAll({
        ...headers,
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      });

      final response = await client.send(request);
      final lineStream = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final line in lineStream) {
        if (!line.startsWith('data: ')) continue;
        final jsonStr = line.substring(6).trim();
        if (jsonStr.isEmpty || jsonStr == '[DONE]') continue;

        try {
          final parsed = jsonDecode(jsonStr) as Map<String, dynamic>;
          // Normalize Gemini quirk: missing surfaceUpdate wrapper
          final normalized = _normalizeGeminiOutput(parsed);
          yield A2uiMessage.fromJson(normalized);
        } on FormatException catch (e) {
          // Malformed JSON — skip this line, continue stream
          logger.warning('GenUI: malformed SSE data', error: e);
        }
      }
    } finally {
      client.close();
    }
  }

  /// Gemini sometimes omits the outer "surfaceUpdate" key.
  Map<String, dynamic> _normalizeGeminiOutput(Map<String, dynamic> parsed) {
    if (parsed.containsKey('surfaceId') &&
        parsed.containsKey('components') &&
        !parsed.containsKey('surfaceUpdate')) {
      return {'surfaceUpdate': parsed};
    }
    return parsed;
  }
}
```

## Handling Gemini Output Quirks

Two known issues when using Gemini models as the agent backend:

### Quirk 1: Missing `surfaceUpdate` Wrapper

Gemini sometimes returns the surface payload without the outer key. Normalize on the backend (Python) AND add client-side resilience:

```dart
// Client-side: if no beginRendering received but 'root' component exists
if (surface.rootComponentId.isEmpty &&
    surface.componentMap.containsKey('root')) {
  surface.rootComponentId = 'root';
}
```

### Quirk 2: Concatenated JSON Objects

Gemini may concatenate multiple JSON objects on one line. The backend MUST handle this with `json.JSONDecoder.raw_decode()` (see `../a2ui-angular/reference/a2ui-protocol.md` for the Python implementation).

## Connection Lifecycle

```
1. Conversation.sendMessage() called
    |
2. Transport opens SSE connection to backend
    |
3. Backend streams A2UI JSONL messages
    |
4. Each message parsed and forwarded to SurfaceController
    |
5. Stream ends (server closes or sends [DONE])
    |
6. Connection closed, surface state is final
    |
7. User interacts -> Conversation.sendAction()
    |
8. Transport sends userAction as POST request
    |
9. Backend responds with new SSE stream -> back to step 3
```

## Reconnection and Timeout

```dart
// Configure transport with timeout and retry
final transport = TriageTransport(
  endpoint: triageEndpoint,
  headers: authHeaders,
);

// In the conversation manager, handle reconnection:
Future<void> sendMessageWithRetry(String text, {int maxRetries = 2}) async {
  for (var attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      await _conversation.sendMessage(text);
      return; // Success
    } on TransportException catch (e) {
      if (attempt == maxRetries) {
        logger.error('Triage transport failed after $maxRetries retries', error: e);
        _showStaticFallbackForm();
        return;
      }
      // Wait before retry (exponential backoff)
      await Future.delayed(Duration(seconds: 1 << attempt));
    }
  }
}
```

## Backend Contract (ADK Triage Agent)

The Flutter client expects the ADK triage agent to:

1. Accept `POST /triage/start` with `{ description: string }` -> return `{ job_id: string }`
2. Accept `GET /triage/{job_id}/stream` -> return SSE stream of A2UI JSONL messages
3. Accept `POST /triage/{job_id}/action` with `UserAction` -> return SSE stream of follow-up
4. Stream `[DONE]` event when conversation turn is complete
5. Return standard A2UI message types only (surfaceUpdate, dataModelUpdate, beginRendering)
6. Use only widget types registered in the client's Catalog
