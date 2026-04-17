# GenUI Security Reference

## Threat Model

GenUI payloads originate from AI agents — which are **untrusted sources**. Even though the agent is "your" agent, its output is shaped by user input (prompt injection risk) and LLM non-determinism. The security boundary is the **Catalog allowlist**.

Agents cannot:
1. Execute arbitrary Dart code on the client
2. Render widgets outside the approved Catalog
3. Inject HTML, scripts, or event handlers (Flutter doesn't use HTML, but the principle applies to widget tree manipulation)
4. Access client-side state, storage, or auth tokens
5. Trigger actions not defined by the client application

## Security Architecture

```
Agent Output (untrusted)
    |
A2UI JSON Payload
    |
+--------------------------------------+
|  SERVER-SIDE VALIDATION              |
|  ADK service validates against       |
|  catalog schema BEFORE streaming     |
+--------------------------------------+
    |
+--------------------------------------+
|  CLIENT-SIDE SECURITY BOUNDARY       |
|  1. Catalog Type Allowlist           |
|  2. Property Type Validation         |
|  3. Input Sanitization               |
|  4. Action Allowlist                 |
|  5. Payload Size Limits              |
+--------------------------------------+
    |
Native Flutter Widget Rendering (trusted)
```

## Required Security Checks

### 1. Catalog Type Allowlist (Mandatory)

Every component `type` MUST be validated against the Catalog before rendering. Unknown types are silently skipped.

```dart
// REQUIRED: Validate before rendering
Widget renderComponent(String type, Map<String, dynamic> properties) {
  final item = catalog.items.firstWhere(
    (i) => i.name == type,
    orElse: () => null,
  );
  if (item == null) {
    logger.warning('GenUI: rejected unknown type "$type"');
    return const SizedBox.shrink(); // Skip unknown types
  }
  return item.builder(context, properties);
}

// FORBIDDEN: Rendering whatever the agent sends
Widget renderComponent(String type, Map<String, dynamic> properties) {
  return widgetRegistry[type]!(properties); // Agent controls rendering
}
```

### 2. Property Type Validation (Mandatory)

All property values from the agent must be validated before use:

```dart
/// Safely extracts a string property, with length limit.
String safeString(Map<String, dynamic> props, String key, {int maxLength = 10000}) {
  final value = props[key];
  if (value is String) return value.substring(0, min(value.length, maxLength));
  if (value is Map<String, dynamic>) {
    if (value.containsKey('literalString')) {
      final str = value['literalString'];
      if (str is String) return str.substring(0, min(str.length, maxLength));
    }
  }
  return '';
}

/// Safely extracts a list of strings, with size limit.
List<String> safeStringList(Map<String, dynamic> props, String key, {int maxItems = 50}) {
  final value = props[key];
  if (value is List) {
    return value
        .whereType<String>()
        .take(maxItems)
        .toList();
  }
  return [];
}

/// Safely extracts a boolean property.
bool safeBool(Map<String, dynamic> props, String key, {bool defaultValue = false}) {
  final value = props[key];
  if (value is bool) return value;
  return defaultValue;
}

/// Safely extracts a number property.
int safeInt(Map<String, dynamic> props, String key, {int defaultValue = 0, int max = 100}) {
  final value = props[key];
  if (value is num) return min(value.toInt(), max);
  return defaultValue;
}
```

### 3. URL Sanitization (Mandatory)

Any URL from agent data must be validated before use:

```dart
/// Validates a URL from agent data — only allows http/https.
String? sanitizeUrl(dynamic value) {
  final urlStr = safeString({'url': value}, 'url');
  if (urlStr.isEmpty) return null;
  try {
    final uri = Uri.parse(urlStr);
    if (uri.scheme != 'http' && uri.scheme != 'https') return null;
    return urlStr;
  } catch (_) {
    return null;
  }
}
```

### 4. Action Allowlist (Mandatory)

Only actions defined by the client application can be triggered:

```dart
/// Allowed actions for PropertyHarbor triage flow.
const _allowedActions = {
  'select_option',     // Dropdown selection
  'submit_text',       // Free text submission
  'upload_photo',      // Photo upload
  'rate_severity',     // Star rating
  'confirm_yes',       // Confirmation - yes
  'confirm_no',        // Confirmation - no
  'submit_triage',     // Final triage submission
  'skip_question',     // Skip optional question
  'go_back',           // Navigate to previous question
};

void handleAction(UserAction action) {
  if (!_allowedActions.contains(action.name)) {
    logger.warning('GenUI: rejected unknown action "${action.name}"');
    return;
  }
  // Process known action
}
```

### 5. Payload Size Limits (Mandatory)

```dart
/// Maximum limits for GenUI payloads.
const kMaxComponents = 200;
const kMaxPropertyLength = 10000; // characters
const kMaxPayloadSize = 1048576; // 1MB
const kMaxWidgets = 50; // per surface
const kMaxDropdownOptions = 50; // per dropdown

/// Validates and truncates a surface update payload.
SurfaceUpdate validatePayload(SurfaceUpdate update) {
  if (update.components.length > kMaxComponents) {
    update = update.copyWith(
      components: update.components.sublist(0, kMaxComponents),
    );
    logger.warning('GenUI: payload truncated — exceeded $kMaxComponents components');
  }
  return update;
}
```

### 6. No Code Execution (Absolute Rule)

Flutter doesn't have `eval()`, but the principle still applies:

```dart
// FORBIDDEN: Dynamic function execution from agent data
Function.apply(properties['handler'], []);
// FORBIDDEN: Dynamic widget creation from agent strings
// FORBIDDEN: Executing agent-provided shell commands or file operations
// FORBIDDEN: Using agent data to construct database queries
```

## PropertyHarbor-Specific Security

### Photo Upload Security

- File type validation: only JPEG/PNG allowed (check magic bytes, not just extension)
- File size limit: 10MB per photo
- Strip EXIF location data before upload (privacy)
- Upload to signed GCS URL, not directly to client storage

### Triage Data Sanitization

- Never store raw agent output in Cloud SQL — extract structured fields only
- Agent responses are logged for debugging but never executed
- Tenant-provided text is sanitized server-side before storage

### Rate Limiting

- SSE connection limited to 1 per triage session
- Max 50 widget interactions per triage session (prevents abuse)
- Triage sessions timeout after 10 minutes of inactivity

## Security Checklist

- [ ] Catalog defines explicit allowlist of widget types
- [ ] Unknown widget types are silently skipped (not rendered)
- [ ] All string properties length-capped (10,000 chars)
- [ ] All list properties size-capped (50 items)
- [ ] URLs validated for http/https protocol only
- [ ] No `Function.apply`, dynamic imports, or code execution from agent data
- [ ] Actions validated against allowlist before processing
- [ ] Photo uploads validated for type, size, and sanitized metadata
- [ ] Payload size limits enforced (200 components, 1MB total)
- [ ] Error boundaries prevent malformed components from crashing the app
- [ ] Fallback to static form when GenUI fails (PropertyHarbor constraint §12)
