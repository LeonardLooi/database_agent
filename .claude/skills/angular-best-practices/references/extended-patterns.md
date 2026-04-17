# Angular Best Practices — Extended Patterns

Detailed code examples moved from `../SKILL.md` for reference.

---

## Rendering Performance (HIGH) — Extended Examples

### Virtual Scrolling for Large Lists

```typescript
import { CdkVirtualScrollViewport, CdkFixedSizeVirtualScroll } from '@angular/cdk/scrolling';

@Component({
  imports: [CdkVirtualScrollViewport, CdkFixedSizeVirtualScroll],
  template: `
    <cdk-virtual-scroll-viewport itemSize="50" class="viewport">
      <div *cdkVirtualFor="let item of items" class="item">
        {{ item.name }}
      </div>
    </cdk-virtual-scroll-viewport>
  `
})
export class LargeListComponent { }
```

### Pure Pipes Over Methods

```typescript
// ✅ CORRECT - Pure pipe, memoized
@Pipe({ name: 'filterActive', standalone: true, pure: true })
export class FilterActivePipe implements PipeTransform {
  transform(items: Item[]): Item[] {
    return items.filter(i => i.active);
  }
}

// Template
@for (item of items() | filterActive; track item.id) { ... }

// ❌ WRONG - Method called every change detection cycle
@for (item of getActiveItems(); track item.id) { ... }
```

### computed() for Derived Data

```typescript
// ✅ CORRECT - Computed, cached until dependencies change
export class ProductStore {
  products = signal<Product[]>([]);
  filter = signal('');

  filteredProducts = computed(() => {
    const f = this.filter().toLowerCase();
    return this.products().filter(p =>
      p.name.toLowerCase().includes(f)
    );
  });
}

// ❌ WRONG - Recalculates every access
get filteredProducts() {
  return this.products.filter(p =>
    p.name.toLowerCase().includes(this.filter)
  );
}
```

---

## State Management (MEDIUM) — Extended Examples

### Selectors to Prevent Re-renders

```typescript
// ✅ CORRECT - Selective subscription
@Component({
  template: `<span>{{ userName() }}</span>`,
})
class HeaderComponent {
  private store = inject(Store);
  // Only re-renders when userName changes
  userName = this.store.selectSignal(selectUserName);
}

// ❌ WRONG - Subscribing to entire state
@Component({
  template: `<span>{{ state().user.name }}</span>`,
})
class HeaderComponent {
  private store = inject(Store);
  // Re-renders on ANY state change
  state = toSignal(this.store);
}
```

### Colocate State with Features

```typescript
// ✅ CORRECT - Feature-scoped store
@Injectable() // NOT providedIn: 'root'
export class ProductStore { }

@Component({
  providers: [ProductStore], // Scoped to component tree
})
export class ProductPageComponent {
  store = inject(ProductStore);
}

// ❌ WRONG - Everything in global store
@Injectable({ providedIn: 'root' })
export class GlobalStore {
  // Contains ALL app state - hard to tree-shake
}
```

---

## Memory Management (LOW-MEDIUM) — Extended Examples

### takeUntilDestroyed for Subscriptions

```typescript
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({...})
export class DataComponent {
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.data$.pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(data => this.process(data));
  }
}

// ❌ WRONG - Manual subscription management
export class DataComponent implements OnDestroy {
  private subscription!: Subscription;

  ngOnInit() {
    this.subscription = this.data$.subscribe(...);
  }

  ngOnDestroy() {
    this.subscription.unsubscribe(); // Easy to forget
  }
}
```

### Prefer Signals Over Subscriptions

```typescript
// ✅ CORRECT - No subscription needed
@Component({
  template: `<div>{{ data().name }}</div>`,
})
export class MyComponent {
  data = toSignal(this.service.data$, { initialValue: null });
}

// ❌ WRONG - Manual subscription
@Component({
  template: `<div>{{ data?.name }}</div>`,
})
export class MyComponent implements OnInit, OnDestroy {
  data: Data | null = null;
  private sub!: Subscription;

  ngOnInit() {
    this.sub = this.service.data$.subscribe((d) => (this.data = d));
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }
}
```

---

## Quick Reference Checklists

### New Component Checklist

- [ ] `changeDetection: ChangeDetectionStrategy.OnPush`
- [ ] `standalone: true`
- [ ] Signals for state (`signal()`, `input()`, `output()`)
- [ ] `inject()` for dependencies
- [ ] `@for` with `track` expression using a unique identifier (not `$index`)

### Performance Review Checklist

- [ ] No methods called in templates — use pure pipes or `computed()`
- [ ] Large lists (>50 items) use `CdkVirtualScrollViewport`
- [ ] Heavy components wrapped in `@defer`
- [ ] All feature routes use `loadChildren` or `loadComponent`
- [ ] Third-party heavy libraries use dynamic `import()`
- [ ] No barrel file re-exports in shared modules

### SSR Checklist

- [ ] `withIncrementalHydration()` configured in `app.config.ts`
- [ ] Critical above-the-fold content renders without `@defer`
- [ ] Non-critical below-fold content uses `@defer (hydrate on viewport)`
- [ ] Interactive-only widgets use `@defer (hydrate on interaction)`
- [ ] Server-fetched data uses `TransferState` to avoid double fetch
