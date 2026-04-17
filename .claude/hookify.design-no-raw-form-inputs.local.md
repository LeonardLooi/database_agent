---
name: design-no-raw-form-inputs
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/app/features/.*\.html$
  - field: content
    operator: regex_match
    pattern: <input\s(?![^>]*formControl)|<select\s(?![^>]*formControl)|<textarea\s(?![^>]*formControl)
  - field: content
    operator: not_contains
    value: "ignore-design"
---
Raw form input detected without reactive form binding. Use daisyUI form components with Angular reactive forms:
- `<input class="input input-bordered" formControlName="...">` not bare `<input>`
- `<select class="select select-bordered" formControlName="...">` not bare `<select>`
- Wrap in `<label class="form-control">` for consistent spacing and labels
- For Flutter: use shared form field wrapper widgets, not raw `TextFormField`
Reference: .claude/skills/angular-spa/reference/angular-conventions.md
