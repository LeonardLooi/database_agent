---
name: design-no-raw-textstyle-dart
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: lib/.*\.dart$
  - field: content
    operator: regex_match
    pattern: TextStyle\(\s*fontSize\s*:
  - field: content
    operator: not_contains
    value: "ignore-design"
---
Raw TextStyle with fontSize detected. Use theme typography instead:
- `Theme.of(context).textTheme.titleMedium`
- `Theme.of(context).textTheme.bodyLarge?.copyWith(...)` for customization
Reference: .claude/skills/ui-standards-tokens/reference/ui-design-tokens.md lines 53-63
