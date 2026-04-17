---
name: design-no-hardcoded-colors-dart
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: lib/.*\.dart$
  - field: content
    operator: regex_match
    pattern: Color\(0x[0-9A-Fa-f]+\)|Colors\.\w+(?!Scheme)
  - field: content
    operator: not_contains
    value: "ignore-design"
---
Hardcoded color detected in Dart file. Use theme tokens instead:
- `Theme.of(context).colorScheme.primary` (not `Colors.blue`)
- `Theme.of(context).colorScheme.onSurface` (not `Color(0xFF000000)`)
Reference: .claude/skills/ui-standards-tokens/reference/ui-design-tokens.md lines 41-51
