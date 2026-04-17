> **Official docs:** https://angular.dev/guide/aria/overview

# Angular Aria — Accessible Headless Components

Angular provides two layers of accessible UI support. The official Angular Aria guide at https://angular.dev/guide/aria/overview is the canonical source for current patterns and APIs.

## What Angular Aria Covers (from official docs)

`@angular/aria` provides **headless, accessible directives** that implement common WAI-ARIA patterns. The library handles keyboard interactions, ARIA attributes, focus management, and screen reader compatibility — you supply HTML structure, styling, and business logic.

```bash
npm install @angular/aria
```

### Available Directives

| Category | Directives |
|----------|-----------|
| Search & Selection | Autocomplete, Listbox, Select, Multiselect, Combobox |
| Navigation & Actions | Menu, Menubar, Toolbar |
| Content Organization | Accordion, Tabs, Tree, Grid |

All directives automatically handle: keyboard navigation (arrows, Enter, Space, Escape), ARIA attribute management, focus management, and RTL language support.

### When to use `@angular/aria` vs `@angular/cdk/a11y`

| Scenario | Use |
|----------|-----|
| Need headless accessible widget (menu, tabs, toolbar) with full control | `@angular/aria` directives |
| Need accessible dropdown, listbox, combobox with CDK | `@angular/cdk` + daisyUI styling |
| Simple static button, badge, alert | daisyUI only (no CDK/aria needed) |
| Custom interactive widget with ARIA roles | `@angular/cdk` `ListKeyManager` |
| Focus trapping (modal, drawer) | `FocusTrap` from `@angular/cdk/a11y` |
| Screen reader announcements | `LiveAnnouncer` from `@angular/cdk/a11y` |

Angular CDK provides headless, accessible UI primitives via `@angular/cdk/a11y`. Angular 21+ also ships `@angular/cdk` with built-in ARIA patterns for common interactive widgets.

## Install CDK

```bash
npm install @angular/cdk
```

## FocusTrap — Modal / Drawer

```typescript
import { Component, ElementRef, inject, viewChild } from '@angular/core';
import { FocusTrapFactory, FocusTrap } from '@angular/cdk/a11y';

@Component({
  selector: 'app-modal',
  standalone: true,
  template: `
    <div 
      #modalPanel
      role="dialog"
      aria-modal="true"
      [attr.aria-label]="title()"
      class="modal-box"
    >
      <ng-content />
    </div>
  `,
})
export class ModalComponent {
  title = input.required<string>();
  private modalPanel = viewChild.required<ElementRef>('modalPanel');
  private focusTrapFactory = inject(FocusTrapFactory);
  private focusTrap?: FocusTrap;

  open() {
    this.focusTrap = this.focusTrapFactory.create(this.modalPanel().nativeElement);
    this.focusTrap.focusInitialElementWhenReady();
  }

  close() {
    this.focusTrap?.destroy();
  }
}
```

## ListKeyManager — Keyboard Navigation (Menu, Listbox, Tabs)

```typescript
import { Component, signal, QueryList, viewChildren, AfterViewInit, inject } from '@angular/core';
import { ActiveDescendantKeyManager } from '@angular/cdk/a11y';
import { DOWN_ARROW, UP_ARROW, ENTER } from '@angular/cdk/keycodes';

// Each item must implement Highlightable
@Component({
  selector: 'app-menu-item',
  standalone: true,
  template: `<li role="option" [class.active]="isActive" [id]="id()">{{ label() }}</li>`,
  host: { '[attr.aria-selected]': 'isActive' },
})
export class MenuItemComponent {
  id = input.required<string>();
  label = input.required<string>();
  isActive = false;
  setActiveStyles() { this.isActive = true; }
  setInactiveStyles() { this.isActive = false; }
}

@Component({
  selector: 'app-menu',
  standalone: true,
  imports: [MenuItemComponent],
  template: `
    <ul
      role="listbox"
      [attr.aria-activedescendant]="activeId()"
      (keydown)="onKeydown($event)"
      tabindex="0"
    >
      @for (item of items(); track item.id) {
        <app-menu-item [id]="item.id" [label]="item.label" />
      }
    </ul>
  `,
})
export class MenuComponent implements AfterViewInit {
  items = input.required<{id: string; label: string}[]>();
  
  private menuItems = viewChildren(MenuItemComponent);
  private keyManager!: ActiveDescendantKeyManager<MenuItemComponent>;
  activeId = signal<string | null>(null);

  ngAfterViewInit() {
    this.keyManager = new ActiveDescendantKeyManager(this.menuItems())
      .withWrap()
      .withTypeAhead();
  }

  onKeydown(event: KeyboardEvent) {
    if (event.keyCode === ENTER) {
      // Handle selection
      return;
    }
    this.keyManager.onKeydown(event);
    this.activeId.set(this.keyManager.activeItem?.id() ?? null);
  }
}
```

## LiveAnnouncer — Screen Reader Announcements

```typescript
import { inject } from '@angular/core';
import { LiveAnnouncer } from '@angular/cdk/a11y';

@Component({...})
export class DataTableComponent {
  private liveAnnouncer = inject(LiveAnnouncer);

  onSortChanged(column: string, direction: string) {
    // Announces to screen readers — no visual change needed
    this.liveAnnouncer.announce(`Sorted by ${column} ${direction}`);
  }

  onLoadComplete(count: number) {
    this.liveAnnouncer.announce(`${count} results loaded`);
  }
}
```

## Accordion Pattern

```typescript
@Component({
  selector: 'app-accordion',
  standalone: true,
  template: `
    @for (item of items(); track item.id) {
      <div>
        <button
          [id]="'btn-' + item.id"
          [attr.aria-expanded]="item.id === expanded()"
          [attr.aria-controls]="'panel-' + item.id"
          (click)="toggle(item.id)"
          class="btn btn-ghost w-full justify-between"
        >
          {{ item.title }}
          <span [class]="expanded() === item.id ? 'rotate-180' : ''">▼</span>
        </button>
        <div
          [id]="'panel-' + item.id"
          role="region"
          [attr.aria-labelledby]="'btn-' + item.id"
          [hidden]="item.id !== expanded()"
          class="p-4"
        >
          {{ item.content }}
        </div>
      </div>
    }
  `,
})
export class AccordionComponent {
  items = input.required<{id: string; title: string; content: string}[]>();
  expanded = signal<string | null>(null);

  toggle(id: string) {
    this.expanded.update(current => current === id ? null : id);
  }
}
```

## Combobox Pattern (Autocomplete)

```typescript
@Component({
  selector: 'app-combobox',
  standalone: true,
  template: `
    <div class="relative">
      <input
        #input
        role="combobox"
        [attr.aria-expanded]="isOpen()"
        [attr.aria-haspopup]="'listbox'"
        [attr.aria-autocomplete]="'list'"
        [attr.aria-controls]="'listbox-' + id"
        [attr.aria-activedescendant]="activeId()"
        class="input input-bordered w-full"
        (input)="onInput($event)"
        (keydown)="onKeydown($event)"
      />
      @if (isOpen()) {
        <ul
          [id]="'listbox-' + id"
          role="listbox"
          class="absolute top-full left-0 right-0 bg-base-100 border rounded shadow-lg z-50"
        >
          @for (option of filtered(); track option.value; let i = $index) {
            <li
              role="option"
              [id]="'option-' + id + '-' + i"
              [attr.aria-selected]="option.value === selected()"
              (click)="select(option)"
              class="px-3 py-2 cursor-pointer hover:bg-base-200"
            >
              {{ option.label }}
            </li>
          }
        </ul>
      }
    </div>
  `,
})
export class ComboboxComponent {
  id = input.required<string>();
  options = input.required<{label: string; value: string}[]>();
  
  selected = signal<string | null>(null);
  query = signal('');
  isOpen = signal(false);
  activeId = signal<string | null>(null);
  
  filtered = computed(() =>
    this.options().filter(o =>
      o.label.toLowerCase().includes(this.query().toLowerCase())
    )
  );

  onInput(event: Event) {
    this.query.set((event.target as HTMLInputElement).value);
    this.isOpen.set(true);
  }

  select(option: {label: string; value: string}) {
    this.selected.set(option.value);
    this.isOpen.set(false);
  }

  onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') this.isOpen.set(false);
  }
}
```

## ARIA Checklist for Interactive Widgets

- [ ] `role` attribute set correctly (`listbox`, `option`, `combobox`, `dialog`, `tab`, `tabpanel`)
- [ ] `aria-expanded` on triggers that open/close panels
- [ ] `aria-controls` linking trigger to controlled region
- [ ] `aria-labelledby` or `aria-label` on every region and dialog
- [ ] `aria-selected` on selectable items
- [ ] `aria-activedescendant` on container with keyboard navigation
- [ ] Focus visible (`:focus-visible`) on all interactive elements
- [ ] `tabindex="0"` on keyboard-navigable containers
- [ ] `hidden` attribute (not `display:none`) on collapsed regions for ARIA hiding
- [ ] `LiveAnnouncer` for dynamic content changes (sort, load, filter)
