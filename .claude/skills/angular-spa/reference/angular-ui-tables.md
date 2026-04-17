# Angular UI Table Patterns

Angular 21+ table and grid components using daisyUI 5.5.5 + TailwindCSS 4.x.
All components use standalone, OnPush, and signal-based APIs.

---

## Section A: Table Tier Decision Framework

Choose the right implementation based on row count.

```
< 100 rows        Simple HTML table
                  Use: existing DataTableComponent (no extra libraries)

100–1,000 rows    Client-side features
                  Use: DataTableComponent + PaginationComponent + client filter

1,000–10,000 rows Server-side pagination
                  Use: Angular HttpClient + signals (TableStateService below)

10,000+ rows      Virtual scrolling
                  Use: @angular/cdk CdkVirtualScrollViewport (Section D below)
```

**Determining row count in practice:**
- Check the API's total count response field at integration time
- If unbounded (e.g., audit log, event stream), default to server-side from the start
- If unsure: start with client-side pagination; migrate to server-side if P95 load > 500 rows

---

## Section B: Pagination Component

```typescript
import {
  Component, ChangeDetectionStrategy, input, output, computed
} from '@angular/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  template: `
    <nav class="flex items-center justify-between mt-4" aria-label="Pagination">
      <div class="flex items-center gap-2">
        <span class="text-sm text-base-content/60">Rows per page:</span>
        <select class="select select-sm select-bordered"
          [value]="pageSize()"
          (change)="onPageSizeChange($event)"
          aria-label="Rows per page">
          @for (size of pageSizeOptions(); track size) {
            <option [value]="size" [selected]="size === pageSize()">{{ size }}</option>
          }
        </select>
        <span class="text-sm text-base-content/60">
          {{ rangeStart() }}–{{ rangeEnd() }} of {{ total() }}
        </span>
      </div>
      <div class="join" role="group" aria-label="Page navigation">
        <button type="button" class="join-item btn btn-sm"
          [class.btn-disabled]="currentPage() === 0"
          [attr.aria-disabled]="currentPage() === 0"
          [attr.aria-label]="'Previous page'"
          (click)="goTo(currentPage() - 1)">«</button>
        @for (page of visiblePages(); track page) {
          @if (page === -1) {
            <button type="button" class="join-item btn btn-sm btn-disabled" aria-hidden="true">…</button>
          } @else {
            <button type="button" class="join-item btn btn-sm"
              [class.btn-active]="page === currentPage()"
              [attr.aria-current]="page === currentPage() ? 'page' : null"
              [attr.aria-label]="'Page ' + (page + 1)"
              (click)="goTo(page)">{{ page + 1 }}</button>
          }
        }
        <button type="button" class="join-item btn btn-sm"
          [class.btn-disabled]="currentPage() === totalPages() - 1"
          [attr.aria-disabled]="currentPage() === totalPages() - 1"
          [attr.aria-label]="'Next page'"
          (click)="goTo(currentPage() + 1)">»</button>
      </div>
    </nav>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PaginationComponent {
  total = input.required<number>();
  currentPage = input<number>(0);
  pageSize = input<number>(10);
  pageSizeOptions = input<number[]>([10, 25, 50, 100]);
  pageChange = output<number>();
  pageSizeChange = output<number>();

  protected readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.total() / this.pageSize()))
  );
  protected readonly rangeStart = computed(() =>
    this.total() === 0 ? 0 : this.currentPage() * this.pageSize() + 1
  );
  protected readonly rangeEnd = computed(() =>
    Math.min((this.currentPage() + 1) * this.pageSize(), this.total())
  );
  protected readonly visiblePages = computed<number[]>(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    if (total <= 7) return Array.from({ length: total }, (_, i) => i);
    const pages: number[] = [0];
    if (current > 2) pages.push(-1);
    for (let i = Math.max(1, current - 1); i <= Math.min(total - 2, current + 1); i++) {
      pages.push(i);
    }
    if (current < total - 3) pages.push(-1);
    pages.push(total - 1);
    return pages;
  });

  protected goTo(page: number): void {
    if (page < 0 || page >= this.totalPages() || page === this.currentPage()) return;
    this.pageChange.emit(page);
  }
  protected onPageSizeChange(event: Event): void {
    const size = Number((event.target as HTMLSelectElement).value);
    this.pageSizeChange.emit(size);
    this.pageChange.emit(0);
  }
}
```

---

## Section C: Server-Side Table Service

Use when row count exceeds 1,000 or data must be filtered/sorted server-side.

```typescript
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { switchMap, tap, catchError, of } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';

interface PagedResponse<T> { items: T[]; total: number; }

@Injectable({ providedIn: 'root' })
export class ServerTableService<T> {
  private readonly http = inject(HttpClient);

  readonly page = signal(0);
  readonly pageSize = signal(25);
  readonly sortField = signal<string | null>(null);
  readonly sortDir = signal<'asc' | 'desc'>('asc');
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);
  private readonly _items = signal<T[]>([]);
  private readonly _total = signal(0);
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly items = this._items.asReadonly();
  readonly total = this._total.asReadonly();
  readonly totalPages = computed(() => Math.ceil(this._total() / this.pageSize()));

  loadFrom(endpoint: string): void {
    toObservable(
      computed(() => ({
        page: this.page(), pageSize: this.pageSize(),
        sortField: this.sortField(), sortDir: this.sortDir()
      }))
    ).pipe(
      tap(() => { this._loading.set(true); this._error.set(null); }),
      switchMap(({ page, pageSize, sortField, sortDir }) => {
        let params = new HttpParams()
          .set('page', page.toString())
          .set('pageSize', pageSize.toString());
        if (sortField) params = params.set('sort', sortField).set('dir', sortDir);
        return this.http.get<PagedResponse<T>>(endpoint, { params }).pipe(
          catchError(err => {
            this._error.set(err?.error?.message ?? 'Failed to load data');
            return of({ items: [], total: 0 });
          })
        );
      })
    ).subscribe(response => {
      this._items.set(response.items);
      this._total.set(response.total);
      this._loading.set(false);
    });
  }

  sortBy(field: string): void {
    if (this.sortField() === field) {
      this.sortDir.update(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortField.set(field);
      this.sortDir.set('asc');
    }
    this.page.set(0);
  }
}
```

---

## Section D: Virtual Scrolling (10,000+ rows)

**Install:** `npm install @angular/cdk`

Structure: `CdkVirtualScrollViewport [itemSize]="48" [style.height.px]="600"` wraps a `<table>` with `*cdkVirtualFor`. Fixed header rendered **outside** the viewport with `sticky top-0`.

```typescript
// imports: [ScrollingModule]  — from '@angular/cdk/scrolling'
// columns = input.required<{ key: string; label: string; width?: string }[]>()
// items = input.required<T[]>()
// rowHeightPx = input<number>(48)   // must match actual rendered row height exactly
// viewportHeightPx = input<number>(600)
// trackById(_i, row) { return row['id']; }  // REQUIRED — prevents full re-render on scroll
```

**Key constraints:**
- `itemSize` must match actual rendered row height — mismatches cause scroll jitter
- `trackBy` is mandatory — without it CDK re-renders every row on each scroll event
- Headers must be rendered outside `CdkVirtualScrollViewport` and positioned sticky
- Import `ScrollingModule` from `@angular/cdk/scrolling`, not from `@angular/cdk`

---

## Section E: Library Comparison

| Need | Recommended | Install |
|------|-------------|---------|
| Full design control, TypeScript-first, headless | **TanStack Table** | `npm install @tanstack/angular-table` |
| Enterprise: grouping, aggregation, export, pivot | **AG Grid Community** | `npm install ag-grid-angular ag-grid-community` |
| Standard sort/filter/paginate, <1K rows | **Existing DataTableComponent** | No install needed |
| 10K+ rows, smooth scroll | **Angular CDK virtual scroll** | `npm install @angular/cdk` |

Rule: introduce a table library only when you need ≥3 features DataTableComponent does not provide.

---

## Section F: Responsive Table Strategies

| Strategy | When to Use |
|----------|-------------|
| **Horizontal scroll** | All columns critical — wrap in `overflow-x-auto` |
| **Priority columns** | `hidden md:table-cell` on lower-priority `<th>` and `<td>` |
| **Card stack** | Row count < 50; mobile-first — `<div class="block md:hidden">` card per row |
| **Truncate & expand** | Many columns — show 2–3 columns + expand row trigger |

**Expand row toggle:**
```typescript
protected readonly expandedRows = signal(new Set<string>());

protected toggleRow(id: string): void {
  this.expandedRows.update(set => {
    const next = new Set(set);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });
}
```

---

## DataTable Component Interface

```typescript
export interface TableColumn<T> {
  key: keyof T & string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

// DataTableComponent inputs/outputs:
// columns = input.required<TableColumn<T>[]>()
// data = input.required<T[]>()
// rowClickable = input<boolean>(false)
// rowClick = output<T>()
// emptyTitle = input<string>('No data')
// emptyDescription = input<string>('No records found')
//
// Internals: sortKey signal, sortDir signal, sortedData computed
// Template: overflow-x-auto > table.table-zebra > thead.bg-base-200 + tbody @for/@empty
// Sort indicator: aria-sort="ascending|descending|none" on <th>
// Empty state: uses <app-empty-state> with colspan
```
