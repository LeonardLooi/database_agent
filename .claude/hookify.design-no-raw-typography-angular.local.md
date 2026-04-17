---
name: design-no-raw-typography-angular
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/.*\.(html|scss|css|ts)$
  - field: content
    operator: regex_match
    pattern: text-\[\d+px\]|text-\[\d+rem\]|text-\[\d+em\]|font-\[.*\]|font-size\s*:\s*\d+
  - field: content
    operator: not_contains
    value: "ignore-design"
---
Raw typography value detected in Angular file. Use Tailwind's typography scale or daisyUI text utilities:
- `text-sm`, `text-base`, `text-lg`, `text-xl` not `text-[14px]`
- `font-sans`, `font-mono` not `font-[Arial]`
- daisyUI component classes handle typography automatically
Reference: .claude/skills/angular-spa/reference/tailwind-v4-config.md
