# Interaction Contracts

Cross-stack behavioral contracts for common UI surfaces. Every surface listed below must follow its contract regardless of framework (Flutter or Angular).

---

## 1. Modals / Dialogs

| Requirement | Flutter | Angular |
|-------------|---------|---------|
| Focus trap — keyboard focus must not escape the modal | `FocusScope` with `autofocus: true` | daisyUI `<dialog>` element (native focus trap) or `cdkTrapFocus` |
| Close on backdrop click | `GestureDetector` on barrier OR `barrierDismissible: true` | `modal.close()` on `<form method="dialog">` or backdrop click handler |
| Close on Escape key | Default in `showDialog` | Default in `<dialog>` element |
| Announce to screen readers | `semanticsLabel` on dialog | `aria-labelledby` pointing to dialog title |
| Return focus to trigger on close | Automatic in Flutter `Navigator.pop` | Manual: save `document.activeElement` before open, restore on close |
| Max width constraint | `ConstrainedBox(maxWidth: 480)` | `max-w-lg` or `max-w-xl` on dialog box |
| Scroll internal content, not the dialog shell | `SingleChildScrollView` inside dialog body | `overflow-y-auto` on body div, not on dialog element |

**NEVER:**
- Open a modal from inside another modal (use navigation or inline expansion instead)
- Use a modal for content that requires comparison with the page behind it (use a slide-over or inline panel)

---

## 2. Forms

| Requirement | Flutter | Angular |
|-------------|---------|---------|
| Every input has a visible label | `InputDecoration(labelText:)` | `<label class="form-control"><span class="label-text">` |
| Validation errors show inline below the field | `InputDecoration(errorText:)` | `@if (control.invalid && control.touched)` with `<span class="text-error">` |
| Submit button shows loading state during async | `ElevatedButton` with `CircularProgressIndicator` swap | `<button class="btn btn-primary" [disabled]="loading()">` with spinner |
| Disable submit when form is invalid | `onPressed: formValid ? submit : null` | `[disabled]="form.invalid"` |
| Show success feedback after submit | `SnackBar` or inline success message | daisyUI `alert alert-success` or toast |
| Show error feedback on submit failure | `SnackBar` with error + retry option | daisyUI `alert alert-error` with retry action |
| Preserve form state on validation error | Never clear fields on failed submit | Never reset form on failed submit |
| Tab order follows visual order | Default in Flutter (top-to-bottom) | Ensure DOM order matches visual order (no CSS reordering) |

**NEVER:**
- Submit a form without client-side validation first
- Show only a generic "Something went wrong" — include the specific field or reason
- Clear the form on error — only clear on successful submit
- Use `alert()` or `window.confirm()` for form feedback

---

## 3. Lists / Tables

| Requirement | Flutter | Angular |
|-------------|---------|---------|
| Empty state — message when no data | Dedicated empty state widget with icon + message + optional CTA | `@if (items().length === 0)` with illustration + message |
| Loading state — skeleton or spinner | `Shimmer` placeholder or `CircularProgressIndicator` | daisyUI `loading loading-spinner` or skeleton divs |
| Error state — retry action | Error widget with "Retry" button calling reload | `@if (error())` with `alert alert-error` + retry button |
| Pagination or virtual scroll for 50+ items | `ListView.builder` (virtual by default) | Virtual scroll (`@for` with `trackBy`) or paginated API |
| Row actions (edit, delete) | `Dismissible` or trailing icon buttons | Icon buttons in last column or dropdown menu |
| Delete confirmation | `showDialog` with confirm/cancel | daisyUI modal with confirm/cancel buttons |
| Sortable columns (tables) | Custom sort state + header tap handler | Click handler on `<th>` with sort indicator icon |
| Responsive — table → card on mobile | `LayoutBuilder` switching between `DataTable` and `Card` list | `hidden lg:table` for table, `lg:hidden` for card layout |

**NEVER:**
- Show a blank page when data is loading — always show loading state
- Show a blank page when data fails to load — always show error + retry
- Render 100+ items without virtual scrolling or pagination
- Delete without confirmation on destructive actions

---

## 4. Navigation / Page Transitions

| Requirement | Flutter | Angular |
|-------------|---------|---------|
| Active link highlighted | `NavigationBar` with `selectedIndex` | `routerLinkActive="active"` with active class styling |
| Loading indicator on route change | `NavigatorObserver` or global loading overlay | Router events subscription showing `loading loading-spinner` |
| Preserve scroll position on back navigation | `PageStorageKey` on scrollable widgets | `scrollPositionRestoration: 'enabled'` in router config |
| 404 / not-found route | Wildcard route to `NotFoundScreen` | Wildcard route `**` to `NotFoundComponent` |
| Breadcrumbs for nested routes (3+ levels) | Custom breadcrumb widget from route data | Component reading `ActivatedRoute` chain |

---

## 5. Feedback / Notifications

| Requirement | Flutter | Angular |
|-------------|---------|---------|
| Success feedback | `SnackBar` with green theme, 3s auto-dismiss | daisyUI `toast` with `alert-success`, 3s auto-dismiss |
| Error feedback | `SnackBar` with error theme, manual dismiss + retry | daisyUI `toast` with `alert-error`, manual dismiss + retry |
| Warning feedback | `SnackBar` with warning theme | daisyUI `toast` with `alert-warning` |
| Position | Bottom center (Flutter default) | Bottom right (`toast` default) |
| Max visible | 1 at a time (queue others) | Max 3 stacked |
| Screen reader announcement | `SnackBar` uses `Semantics` automatically | `aria-live="polite"` on toast container |

**NEVER:**
- Use `print()` or `console.log()` as user feedback — always use visible UI
- Show success and error at the same time
- Auto-dismiss error messages — user must acknowledge errors

---

## 6. Responsive Breakpoints

Consistent across both stacks:

| Name | Width | Target |
|------|-------|--------|
| `sm` | 640px | Large phones (landscape) |
| `md` | 768px | Tablets |
| `lg` | 1024px | Small laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large desktops |

- **Mobile-first:** Default styles target mobile, use breakpoint prefixes to add desktop behavior
- **Flutter:** Use `LayoutBuilder` or `MediaQuery` with `AppBreakpoints` constants
- **Angular:** Use Tailwind responsive prefixes (`sm:`, `md:`, `lg:`)

---

## Applying These Contracts

When building any UI surface:

1. **Identify which contract applies** (modal, form, list, navigation, feedback)
2. **Check every row** in the requirement table for that contract
3. **Implement all requirements** — not just the happy path
4. **Test the unhappy paths:** empty, loading, error, edge cases
5. **If a requirement doesn't apply**, add `// ignore-design: [reason]` with explanation
