# Accessibility Audit Checklist (WCAG 2.1 — Flutter)

## 1. Semantics Widget Usage

- [ ] Interactive elements have semantic labels
- [ ] Images have `Semantics(image: true, label: ...)`
- [ ] Decorative elements use `excludeSemantics: true`
- [ ] Buttons use `Semantics(button: true, ...)`
- [ ] Live regions for dynamic content updates

## 2. Color Contrast (WCAG 2.1)

- [ ] Normal text: minimum 4.5:1 ratio
- [ ] Large text (18pt+): minimum 3:1 ratio
- [ ] UI components: minimum 3:1 ratio
- [ ] Using `ColorScheme` for accessible defaults
- [ ] Not relying on color alone to convey information

## 3. Touch Targets

- [ ] Minimum 48x48 dp tap targets
- [ ] Adequate spacing between interactive elements
- [ ] `IconButton` or padded `GestureDetector` used

## 4. Dynamic Text Scaling

- [ ] Uses `MediaQuery.textScalerOf(context)`
- [ ] No fixed heights that clip scaled text
- [ ] Text readable at 200% scale
- [ ] `ConstrainedBox` instead of fixed `SizedBox` for text

## 5. Focus Management

- [ ] Logical focus order with `FocusTraversalGroup`
- [ ] Focus visible indicators present
- [ ] Programmatic focus management where needed
- [ ] Modal dialogs trap focus appropriately

## 6. Screen Reader Support

- [ ] `SemanticsService.announce()` for important updates
- [ ] Form fields have `labelText` in `InputDecoration`
- [ ] Error messages announced to screen readers
- [ ] `MergeSemantics` groups related elements

## Output Format

```markdown
## Accessibility Audit Results

### Critical (Blocks users)
- **[A11Y-001]** Missing semantic label on button
  - File: `file_path:line_number`
  - Issue: IconButton without semantic label
  - Fix: Add `Semantics(label: 'Submit login', button: true, child: ...)`

### Important (Degrades experience)
- **[A11Y-002]** Low color contrast
  - File: `file_path:line_number`
  - Ratio: 3.2:1 (required: 4.5:1 for normal text)
  - Fix: Use `colorScheme.onSurface` for text

### Suggestions
- **[A11Y-003]** Consider adding live region
  - File: `file_path:line_number`
  - Recommendation: Add `Semantics(liveRegion: true, ...)` for dynamic updates
```

## Testing Recommendations

- [ ] Test with TalkBack (Android)
- [ ] Test with VoiceOver (iOS)
- [ ] Test at 200% font scale
- [ ] Test with high contrast mode
