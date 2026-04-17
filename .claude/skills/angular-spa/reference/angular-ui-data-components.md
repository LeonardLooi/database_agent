# Angular UI Data Display Components

Reusable Angular 21+ data display components using daisyUI 5.5.5 + TailwindCSS 4.x.
All components use standalone, OnPush, and signal-based APIs.

---

## Section A: Table Tier Decision Framework

Choose the right implementation based on row count. Using a heavier tier than necessary adds bundle size and complexity with no benefit.

```
< 100 rows        Simple HTML table
                  Use: existing DataTableComponent (no extra libraries)
                  Avoid: adding pagination — users can scan the full set

100–1,000 rows    Client-side features
                  Use: DataTableComponent + PaginationComponent (below) + client filter
                  Avoid: virtual scrolling — overhead not justified at this scale

1,000–10,000 rows Server-side pagination
                  Use: Angular HttpClient + signals (TableStateService below)
                  Avoid: loading all rows client-side — kills memory and TTI

10,000+ rows      Virtual scrolling
                  Use: @angular/cdk CdkVirtualScrollViewport (Section D below)
                  Avoid: pagination at this scale — virtual scroll is smoother UX
```

**Determining row count in practice:**
- Check the API's total count response field at integration time
- If unbounded (e.g., audit log, event stream), default to server-side from the start
- If unsure: start with client-side pagination; migrate to server-side if P95 load > 500 rows

---

## Section B: Pagination Component (client-side, Angular signals)

```typescript
import {
  Component, ChangeDetectionStrategy, input, output, signal, computed
} from '@angular/core';

@Component({
  selector: 'app-pagination',
  standalone: true,
  template: `
    <nav class="flex items-center justify-between mt-4" aria-label="Pagination">
      <!-- Page size selector -->
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

      <!-- Page buttons -->
      <div class="join" role="group" aria-label="Page navigation">
        <button type="button" class="join-item btn btn-sm"
          [class.btn-disabled]="currentPage() === 0"
          [attr.aria-disabled]="currentPage() === 0"
          [attr.aria-label]="'Previous page'"
          (click)="goTo(currentPage() - 1)">
          «
        </button>

        @for (page of visiblePages(); track page) {
          @if (page === -1) {
            <button type="button" class="join-item btn btn-sm btn-disabled" aria-hidden="true">…</button>
          } @else {
            <button type="button" class="join-item btn btn-sm"
              [class.btn-active]="page === currentPage()"
              [attr.aria-current]="page === currentPage() ? 'page' : null"
              [attr.aria-label]="'Page ' + (page + 1)"
              (click)="goTo(page)">
              {{ page + 1 }}
            </button>
          }
        }

        <button type="button" class="join-item btn btn-sm"
          [class.btn-disabled]="currentPage() === totalPages() - 1"
          [attr.aria-disabled]="currentPage() === totalPages() - 1"
          [attr.aria-label]="'Next page'"
          (click)="goTo(currentPage() + 1)">
          »
        </button>
      </div>
    </nav>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PaginationComponent {
  // Inputs
  total = input.required<number>();
  currentPage = input<number>(0);
  pageSize = input<number>(10);
  pageSizeOptions = input<number[]>([10, 25, 50, 100]);

  // Outputs
  pageChange = output<number>();
  pageSizeChange = output<number>();

  // Derived
  protected readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.total() / this.pageSize()))
  );
  protected readonly rangeStart = computed(() =>
    this.total() === 0 ? 0 : this.currentPage() * this.pageSize() + 1
  );
  protected readonly rangeEnd = computed(() =>
    Math.min((this.currentPage() + 1) * this.pageSize(), this.total())
  );

  // Show at most 7 page buttons with ellipsis markers (-1)
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
    this.pageChange.emit(0); // reset to first page on size change
  }
}

// Usage with DataTableComponent (client-side slice)
@Component({
  selector: 'app-paginated-table-demo',
  standalone: true,
  imports: [DataTableComponent, PaginationComponent],
  template: `
    <app-data-table [columns]="columns" [data]="pagedItems()" />
    <app-pagination
      [total]="allItems().length"
      [currentPage]="currentPage()"
      [pageSize]="pageSize()"
      (pageChange)="currentPage.set($event)"
      (pageSizeChange)="onPageSizeChange($event)" />
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PaginatedTableDemoComponent<T extends Record<string, unknown>> {
  protected readonly allItems = signal<T[]>([]);
  protected readonly currentPage = signal(0);
  protected readonly pageSize = signal(10);

  protected readonly totalPages = computed(() =>
    Math.ceil(this.allItems().length / this.pageSize())
  );

  protected readonly pagedItems = computed(() => {
    const start = this.currentPage() * this.pageSize();
    return this.allItems().slice(start, start + this.pageSize());
  });

  protected onPageSizeChange(size: number): void {
    this.pageSize.set(size);
    this.currentPage.set(0);
  }

  // columns wired via input in real usage
  protected readonly columns: TableColumn<T>[] = [];
}
```

---

## Section C: Server-Side Table Service Pattern

Use when row count exceeds 1,000 or data must be filtered/sorted server-side.

```typescript
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { switchMap, tap, catchError, of } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';

// ---- Types ----

export interface TableState<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  sortField: string | null;
  sortDir: 'asc' | 'desc';
  loading: boolean;
  error: string | null;
}

interface PagedResponse<T> {
  items: T[];
  total: number;
}

// ---- Service ----

@Injectable({ providedIn: 'root' })
export class ServerTableService<T> {
  private readonly http = inject(HttpClient);

  // Writable state signals
  readonly page = signal(0);
  readonly pageSize = signal(25);
  readonly sortField = signal<string | null>(null);
  readonly sortDir = signal<'asc' | 'desc'>('asc');

  // Internal loading/error signals
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);
  private readonly _items = signal<T[]>([]);
  private readonly _total = signal(0);

  // Public read-only derived state
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly items = this._items.asReadonly();
  readonly total = this._total.asReadonly();

  readonly totalPages = computed(() => Math.ceil(this._total() / this.pageSize()));

  // Fetch triggers automatically whenever any query signal changes.
  // Call loadFrom(endpoint) once to register the endpoint, then mutate
  // page/pageSize/sortField/sortDir to trigger re-fetch.
  loadFrom(endpoint: string): void {
    // Build params signal from reactive inputs
    toObservable(
      computed(() => ({
        page: this.page(),
        pageSize: this.pageSize(),
        sortField: this.sortField(),
        sortDir: this.sortDir()
      }))
    ).pipe(
      tap(() => {
        this._loading.set(true);
        this._error.set(null);
      }),
      switchMap(({ page, pageSize, sortField, sortDir }) => {
        let params = new HttpParams()
          .set('page', page.toString())
          .set('pageSize', pageSize.toString());
        if (sortField) {
          params = params.set('sort', sortField).set('dir', sortDir);
        }
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
    this.page.set(0); // reset to page 1 on sort change
  }
}

// ---- Component using the service ----

@Component({
  selector: 'app-server-table',
  standalone: true,
  imports: [DataTableComponent, PaginationComponent],
  template: `
    @if (svc.loading()) {
      <div class="flex justify-center p-8" role="status" aria-label="Loading data">
        <span class="loading loading-spinner loading-lg"></span>
      </div>
    } @else if (svc.error()) {
      <div class="alert alert-error" role="alert">
        <span>{{ svc.error() }}</span>
      </div>
    } @else {
      <app-data-table
        [columns]="columns"
        [data]="svc.items()"
        (rowClick)="onRowClick($event)" />
      <app-pagination
        [total]="svc.total()"
        [currentPage]="svc.page()"
        [pageSize]="svc.pageSize()"
        (pageChange)="svc.page.set($event)"
        (pageSizeChange)="svc.pageSize.set($event)" />
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ServerTableComponent<T extends Record<string, unknown>> {
  protected readonly svc = inject(ServerTableService<T>);
  protected readonly columns: TableColumn<T>[] = []; // set via input in real usage

  ngOnInit(): void {
    this.svc.loadFrom('/api/my-resource');
  }

  protected onRowClick(row: T): void {
    // handle row click
  }
}
```

---

## Section D: Virtual Scrolling (10,000+ rows)

**Install:** `npm install @angular/cdk`

Virtual scrolling renders only the rows in the viewport — the DOM size stays fixed regardless of dataset size. Required when rendering 10K+ rows.

```typescript
import {
  Component, ChangeDetectionStrategy, input, signal, computed
} from '@angular/core';
import { ScrollingModule, CdkVirtualScrollViewport } from '@angular/cdk/scrolling';

interface VirtualRow {
  id: string | number;
  [key: string]: unknown;
}

@Component({
  selector: 'app-virtual-table',
  standalone: true,
  imports: [ScrollingModule],
  template: `
    <div class="overflow-x-auto rounded-box border border-base-300">
      <!-- Fixed header — rendered outside the virtual scroll viewport -->
      <table class="table table-zebra w-full">
        <thead class="bg-base-200 sticky top-0 z-10">
          <tr>
            @for (col of columns(); track col.key) {
              <th [style.width]="col.width">{{ col.label }}</th>
            }
          </tr>
        </thead>
      </table>

      <!-- Virtual scroll body -->
      <cdk-virtual-scroll-viewport
        [itemSize]="rowHeightPx()"
        [style.height.px]="viewportHeightPx()"
        class="w-full">
        <table class="table table-zebra w-full">
          <tbody>
            <tr *cdkVirtualFor="let row of items(); trackBy: trackById"
              class="hover:bg-base-200/50 transition-colors">
              @for (col of columns(); track col.key) {
                <td [style.width]="col.width">{{ row[col.key] }}</td>
              }
            </tr>
          </tbody>
        </table>
      </cdk-virtual-scroll-viewport>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class VirtualTableComponent<T extends VirtualRow> {
  columns = input.required<{ key: keyof T & string; label: string; width?: string }[]>();
  items = input.required<T[]>();
  rowHeightPx = input<number>(48);       // must match actual rendered row height in px
  viewportHeightPx = input<number>(600); // container height — set to fit your layout

  // trackBy is REQUIRED for virtual scroll performance
  protected trackById(_index: number, row: VirtualRow): string | number {
    return row['id'];
  }
}
```

**Key constraints:**
- `itemSize` must match the actual rendered row height in pixels — mismatches cause scroll jitter
- `trackBy` is mandatory — without it, CDK re-renders every row on each scroll event
- Headers must be rendered outside `CdkVirtualScrollViewport` and positioned sticky
- Do NOT use `table-zebra` striping based on DOM index — rows recycle and zebra will flicker; use data-driven striping instead (`[class.bg-base-200]="row.index % 2 === 0"`)
- Import `ScrollingModule` from `@angular/cdk/scrolling`, not from `@angular/cdk`

---

## Section E: Library Comparison

| Need | Recommended Library | Install |
|------|--------------------|---------|
| Full design control, TypeScript-first, headless | **TanStack Table** | `npm install @tanstack/angular-table` |
| Enterprise features out of the box: grouping, aggregation, export, pivot | **AG Grid Community** | `npm install ag-grid-angular ag-grid-community` |
| Standard sort/filter/paginate, daisyUI styling, <1K rows | **Existing DataTableComponent** | No install needed |
| 10K+ rows, smooth scroll, no libraries | **Angular CDK virtual scroll** | `npm install @angular/cdk` |

**When NOT to add a library:**

- DataTableComponent + PaginationComponent handles sort + filter + paginate for <1K rows — that covers ~80% of admin table use cases
- Adding TanStack or AG Grid for a simple CRUD list adds ~50–200 KB to the bundle for zero user-visible benefit
- Rule of thumb: introduce a table library only when you need ≥3 features it provides that DataTableComponent does not (e.g., inline editing + column resize + export)

**TanStack Table minimal setup:**

```typescript
import {
  Component, ChangeDetectionStrategy, signal, inject
} from '@angular/core';
import {
  createAngularTable, FlexRenderDirective,
  getCoreRowModel, getSortedRowModel, getPaginationRowModel,
  type ColumnDef, type SortingState
} from '@tanstack/angular-table';

@Component({
  selector: 'app-tanstack-table',
  standalone: true,
  imports: [FlexRenderDirective],
  template: `
    <div class="overflow-x-auto rounded-box border border-base-300">
      <table class="table table-zebra">
        <thead class="bg-base-200">
          @for (headerGroup of table.getHeaderGroups(); track headerGroup.id) {
            <tr>
              @for (header of headerGroup.headers; track header.id) {
                <th (click)="header.column.getToggleSortingHandler()?.($event)"
                  [class.cursor-pointer]="header.column.getCanSort()">
                  <ng-container *flexRender="header.column.columnDef.header; props: header.getContext()" />
                  {{ { asc: ' ↑', desc: ' ↓' }[header.column.getIsSorted() as string] ?? '' }}
                </th>
              }
            </tr>
          }
        </thead>
        <tbody>
          @for (row of table.getRowModel().rows; track row.id) {
            <tr class="hover:bg-base-200/50">
              @for (cell of row.getVisibleCells(); track cell.id) {
                <td>
                  <ng-container *flexRender="cell.column.columnDef.cell; props: cell.getContext()" />
                </td>
              }
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TanStackTableComponent<T> {
  private readonly sorting = signal<SortingState>([]);

  // Define columns externally and pass as input; shown inline for brevity
  protected readonly table = createAngularTable<T>(() => ({
    data: [],
    columns: [] as ColumnDef<T>[],
    state: { sorting: this.sorting() },
    onSortingChange: updater => {
      this.sorting.update(s => typeof updater === 'function' ? updater(s) : updater);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel()
  }));
}
```

---

## Section F: Responsive Table Strategies

| Strategy | When to Use | Implementation |
|----------|-------------|----------------|
| **Horizontal scroll** | All columns critical; data is dense | Wrap table in `overflow-x-auto` — preserves full structure, simplest |
| **Priority columns** | Some columns are secondary on mobile | `hidden md:table-cell` on lower-priority `<th>` and `<td>` |
| **Card stack** | Row count < 50; mobile-first product | Use `@media` breakpoint: `<div class="block md:hidden">` card per row |
| **Truncate & expand** | Many columns; users need occasional detail | Show 2–3 columns + expand row trigger (`+` icon) to reveal rest inline |

**Horizontal scroll (default — use first):**

```html
<div class="overflow-x-auto rounded-box border border-base-300 -mx-4 px-4 md:mx-0 md:px-0">
  <table class="table table-zebra min-w-[640px]">
    <!-- min-w forces scroll on small screens; table won't collapse -->
  </table>
</div>
```

**Priority columns:**

```html
<!-- Hide "Notes" and "Created At" columns on mobile -->
<th class="hidden lg:table-cell">Notes</th>
<th class="hidden md:table-cell">Created At</th>

<!-- Matching td cells must carry the same classes -->
<td class="hidden lg:table-cell">{{ row.notes }}</td>
<td class="hidden md:table-cell">{{ row.createdAt }}</td>
```

**Card stack per row (mobile only):**

```html
<!-- Mobile card layout -->
<div class="block md:hidden space-y-3">
  @for (row of data(); track row.id) {
    <div class="card bg-base-100 border border-base-300 p-4 space-y-1">
      <div class="font-semibold">{{ row.name }}</div>
      <div class="text-sm text-base-content/60">{{ row.email }}</div>
      <div class="badge badge-ghost">{{ row.status }}</div>
    </div>
  }
</div>

<!-- Desktop table layout -->
<div class="hidden md:block overflow-x-auto">
  <table class="table table-zebra">...</table>
</div>
```

**Expand row for overflow columns:**

```typescript
// In DataTableComponent or inline:
protected readonly expandedRows = signal(new Set<string>());

protected toggleRow(id: string): void {
  this.expandedRows.update(set => {
    const next = new Set(set);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });
}
```

```html
<tr class="hover:bg-base-200/50">
  <td>{{ row.name }}</td>
  <td>{{ row.email }}</td>
  <td>
    <button type="button" class="btn btn-xs btn-ghost"
      [attr.aria-expanded]="expandedRows().has(row.id)"
      [attr.aria-label]="'Toggle details for ' + row.name"
      (click)="toggleRow(row.id)">
      {{ expandedRows().has(row.id) ? '−' : '+' }}
    </button>
  </td>
</tr>
@if (expandedRows().has(row.id)) {
  <tr class="bg-base-200/30">
    <td [attr.colspan]="columns().length + 1" class="p-4">
      <!-- Full row detail view -->
      <dl class="grid grid-cols-2 gap-2 text-sm">
        <dt class="text-base-content/60">Notes</dt>
        <dd>{{ row.notes }}</dd>
        <dt class="text-base-content/60">Created</dt>
        <dd>{{ row.createdAt }}</dd>
      </dl>
    </td>
  </tr>
}
```

---

## Component Templates

---

## Card Component

```typescript
import {
  Component, ChangeDetectionStrategy, signal, computed,
  input, output
} from '@angular/core';

@Component({
  selector: 'app-example-card',

  template: `
    <article class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">{{ title() }}</h2>
        @if (loading()) {
          <div class="space-y-2">
            <div class="skeleton h-4 w-full"></div>
            <div class="skeleton h-4 w-3/4"></div>
          </div>
        } @else {
          <p class="text-base-content/70">{{ content() }}</p>
        }
        <div class="card-actions justify-end mt-4">
          <button type="button" class="btn btn-primary"
            [class.btn-disabled]="loading()"
            [attr.aria-busy]="loading()"
            (click)="handleAction()">
            @if (loading()) {
              <span class="loading loading-spinner loading-sm"></span>
            }
            {{ actionLabel() }}
          </button>
        </div>
      </div>
    </article>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ExampleCardComponent {
  title = input.required<string>();
  content = input<string>('');
  actionLabel = input<string>('Submit');
  loading = input<boolean>(false);
  action = output<void>();

  protected handleAction(): void {
    if (!this.loading()) this.action.emit();
  }
}
```

## Empty State

```typescript
import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';

@Component({
  selector: 'app-empty-state',

  template: `
    <div class="hero min-h-[300px] bg-base-200 rounded-box">
      <div class="hero-content text-center">
        <div class="max-w-md">
          <div class="text-6xl mb-4" aria-hidden="true">{{ icon() }}</div>
          <h2 class="text-2xl font-bold">{{ title() }}</h2>
          <p class="py-4 text-base-content/60">{{ description() }}</p>
          @if (actionLabel()) {
            <button type="button" class="btn btn-primary" (click)="action.emit()">
              {{ actionLabel() }}
            </button>
          }
        </div>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EmptyStateComponent {
  icon = input<string>('');
  title = input.required<string>();
  description = input.required<string>();
  actionLabel = input<string>('');
  action = output<void>();
}
```

## Skeleton Loader

```typescript
import { Component, ChangeDetectionStrategy, input } from '@angular/core';

@Component({
  selector: 'app-skeleton',

  template: `
    <div class="animate-pulse" role="status" aria-label="Loading content">
      @for (row of rowsArray(); track $index) {
        <div class="flex items-start gap-4 mb-4">
          @if (showAvatar()) {
            <div class="skeleton w-12 h-12 rounded-full shrink-0"></div>
          }
          <div class="flex-1 space-y-3">
            <div class="skeleton h-4 w-3/4"></div>
            <div class="skeleton h-4 w-1/2"></div>
          </div>
        </div>
      }
      <span class="sr-only">Loading...</span>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SkeletonComponent {
  rows = input<number>(3);
  showAvatar = input<boolean>(true);
  protected rowsArray = () => Array.from({ length: this.rows() });
}
```

## Data Table

```typescript
import {
  Component, ChangeDetectionStrategy, input, signal, computed, output
} from '@angular/core';
import { EmptyStateComponent } from './empty-state.component';

export interface TableColumn<T> {
  key: keyof T & string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

@Component({
  selector: 'app-data-table',

  imports: [EmptyStateComponent],
  template: `
    <div class="overflow-x-auto rounded-box border border-base-300">
      <table class="table table-zebra">
        <thead class="bg-base-200">
          <tr>
            @for (col of columns(); track col.key) {
              <th [class.cursor-pointer]="col.sortable" [style.width]="col.width"
                [style.text-align]="col.align || 'left'"
                (click)="col.sortable && sort(col.key)"
                [attr.aria-sort]="sortKey() === col.key ? (sortDir() === 'asc' ? 'ascending' : 'descending') : 'none'">
                <div class="flex items-center gap-2">
                  <span>{{ col.label }}</span>
                  @if (col.sortable) {
                    <span class="text-base-content/40 text-sm">
                      {{ sortKey() === col.key ? (sortDir() === 'asc' ? '↑' : '↓') : '↕' }}
                    </span>
                  }
                </div>
              </th>
            }
          </tr>
        </thead>
        <tbody>
          @for (row of sortedData(); track $index) {
            <tr class="hover:bg-base-200/50 transition-colors"
              [class.cursor-pointer]="rowClickable()"
              (click)="rowClickable() && rowClick.emit(row)">
              @for (col of columns(); track col.key) {
                <td [style.text-align]="col.align || 'left'">{{ row[col.key] }}</td>
              }
            </tr>
          } @empty {
            <tr>
              <td [attr.colspan]="columns().length" class="p-0">
                <app-empty-state [title]="emptyTitle()" [description]="emptyDescription()" />
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DataTableComponent<T extends Record<string, unknown>> {
  columns = input.required<TableColumn<T>[]>();
  data = input.required<T[]>();
  rowClickable = input<boolean>(false);
  rowClick = output<T>();
  emptyTitle = input<string>('No data');
  emptyDescription = input<string>('No records found');

  protected readonly sortKey = signal<string | null>(null);
  protected readonly sortDir = signal<'asc' | 'desc'>('asc');

  protected readonly sortedData = computed(() => {
    const key = this.sortKey();
    const result = [...this.data()];
    if (!key) return result;
    const mod = this.sortDir() === 'asc' ? 1 : -1;
    return result.sort((a, b) => {
      if (a[key] == null) return mod;
      if (b[key] == null) return -mod;
      return a[key] < b[key] ? -mod : a[key] > b[key] ? mod : 0;
    });
  });

  protected sort(key: string): void {
    if (this.sortKey() === key) {
      this.sortDir.update(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortKey.set(key);
      this.sortDir.set('asc');
    }
  }
}
```

## Responsive Navigation

```typescript
import {
  Component, ChangeDetectionStrategy, signal, input
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem { label: string; path: string; icon?: string; }

@Component({
  selector: 'app-responsive-nav',

  imports: [RouterLink, RouterLinkActive],
  template: `
    <div class="drawer lg:drawer-open">
      <input id="nav-drawer" type="checkbox" class="drawer-toggle"
        [checked]="drawerOpen()" (change)="toggleDrawer($event)" />
      <div class="drawer-content flex flex-col min-h-screen">
        <header class="navbar bg-base-100 border-b border-base-300 lg:hidden sticky top-0 z-30">
          <div class="flex-none">
            <label for="nav-drawer" class="btn btn-square btn-ghost" aria-label="Open navigation">
              <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
              </svg>
            </label>
          </div>
          <div class="flex-1"><span class="text-xl font-bold px-2">{{ title() }}</span></div>
        </header>
        <main class="flex-1 p-4 lg:p-6"><ng-content></ng-content></main>
      </div>
      <aside class="drawer-side z-40">
        <label for="nav-drawer" class="drawer-overlay" aria-label="Close navigation"></label>
        <div class="bg-base-200 min-h-full w-64 flex flex-col">
          <div class="p-4 border-b border-base-300">
            <h1 class="text-xl font-bold">{{ title() }}</h1>
          </div>
          <nav class="flex-1 p-4">
            <ul class="menu gap-1">
              @for (item of navItems(); track item.path) {
                <li>
                  <a [routerLink]="item.path" routerLinkActive="active"
                    [routerLinkActiveOptions]="{ exact: item.path === '/' }"
                    (click)="drawerOpen.set(false)">
                    @if (item.icon) { <span>{{ item.icon }}</span> }
                    {{ item.label }}
                  </a>
                </li>
              }
            </ul>
          </nav>
        </div>
      </aside>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResponsiveNavComponent {
  title = input<string>('App');
  navItems = input<NavItem[]>([]);
  protected readonly drawerOpen = signal(false);

  protected toggleDrawer(event: Event): void {
    this.drawerOpen.set((event.target as HTMLInputElement).checked);
  }
}
```

## Expandable Section

```typescript
import { Component, ChangeDetectionStrategy, input, signal } from '@angular/core';

@Component({
  selector: 'app-expandable-section',

  template: `
    <div class="collapse collapse-arrow bg-base-200 rounded-box">
      <input type="checkbox" [checked]="isExpanded()" (change)="isExpanded.update(v => !v)"
        [attr.aria-expanded]="isExpanded()" />
      <div class="collapse-title text-lg font-medium">
        {{ title() }}
        @if (badge()) { <span class="badge badge-sm ml-2">{{ badge() }}</span> }
      </div>
      <div class="collapse-content"><div class="pt-2"><ng-content></ng-content></div></div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ExpandableSectionComponent {
  title = input.required<string>();
  badge = input<string>('');
  defaultExpanded = input<boolean>(false);
  protected readonly isExpanded = signal(false);
}
```

---

## Chat / Agent UI — Visual Quality Baseline

When building any chat or conversational agent UI (message list + input bar pattern), apply ALL of the following from the first scaffold. Do not wait for user feedback to add these.

### Layout
- Outer container: `h-screen flex flex-col overflow-hidden` — never `min-h-screen` (causes footer scroll-away)
- Header: `flex-shrink-0` — must not grow or shrink
- Message list: `flex-1 overflow-y-auto` — scrolls independently
- Input bar: `flex-shrink-0` at bottom — always visible, never scrolls away
- Empty state: center the input bar vertically with `min-h-[55vh] flex flex-col items-center justify-center`
- After first message: move input bar to sticky footer pattern

### Cards
- Use `card bg-base-100 shadow-sm border border-base-200` — not plain divs
- Card content: `card-body p-4` with `card-title text-sm font-semibold`
- Price / key stats: `text-lg font-bold text-neutral` for emphasis
- Secondary text: `text-base-content/60 text-xs`

### Buttons
- Primary action: `btn btn-neutral rounded-xl` — not `btn btn-primary` (often invisible on dark themes)
- Text on dark buttons must be `text-neutral-content` — always verify contrast
- Disabled state: `[disabled]="loading()"` on all submit buttons

### Loading states
- Inline spinner in button: `<span class="loading loading-spinner loading-sm"></span>`
- Agent thinking indicator: `<span class="loading loading-dots loading-sm text-neutral"></span>` with explanatory text
- Never show a blank area while waiting — always show a loading indicator

### Empty state
- Show branded icon, headline, subtitle, and suggestion chips
- Suggestion chips: `btn btn-sm bg-base-100 border border-base-300 hover:bg-neutral hover:text-neutral-content`

### Auto-scroll
- Inject `viewChild<ElementRef>('messageContainer')`
- Use `effect()` to watch the messages signal and scroll to bottom: `el.scrollTop = el.scrollHeight` inside a `setTimeout(..., 50)`

### Smoke test before reporting done
Open the app and verify:
- [ ] Header visible and not overlapping content
- [ ] Input bar always visible at bottom (even when messages overflow)
- [ ] Cards have visible borders/shadows — not flat invisible boxes
- [ ] Buttons have visible text (check contrast on dark background)
- [ ] Loading spinner appears when request is in-flight

---

## Bug 10 — Missing left padding after layout change

**What happened:** After modifying the outer container's CSS class, the `px-4`/`px-6` padding was dropped. Content rendered flush against the left edge of the viewport with zero margin.

## Layout Padding — Always Preserve on Refactor

When refactoring the outer container or changing flex/grid structure, ALWAYS verify padding is carried forward.

Checklist when changing `<div class="...">` on an outer container:
- [ ] `px-4` or `px-6` still present on content wrapper (not just outer container)
- [ ] `max-w-4xl mx-auto` still applied to centre-constrain content
- [ ] Inner `<main>` and `<footer>` both have their own horizontal padding

Pattern that survives layout refactors:
```html
<!-- Outer: layout only, no padding -->
<div class="h-screen flex flex-col overflow-hidden">
  <!-- Inner: content width and padding -->
  <main class="flex-1 overflow-y-auto">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <!-- content here -->
    </div>
  </main>
  <footer class="flex-shrink-0 px-4 py-4">
    <div class="max-w-4xl mx-auto">
      <!-- input bar here -->
    </div>
  </footer>
</div>
```

Never put padding only on the outermost div — it gets lost when structure changes.

---

## Bug 11 — Invisible text on dark button

**What happened:** A button used `btn btn-neutral` but the text color was not set to `text-neutral-content`. On a dark neutral background, the text was invisible.

## Button Text Contrast — Always Verify

When using DaisyUI semantic button classes, never assume text color is set automatically.

| Button class | Required text class |
|---|---|
| `btn btn-neutral` | `text-neutral-content` (explicit or via DaisyUI) |
| `btn btn-primary` | `text-primary-content` |
| `btn btn-base-100` (custom) | `text-base-content` explicitly |

❌ Common mistake:
```html
<button class="btn btn-neutral">Search</button>
<!-- text may be invisible if neutral bg = dark and text defaults to dark -->
```

✅ Safe pattern — always include text color:
```html
<button class="btn btn-neutral text-neutral-content">Search</button>
```

**Smoke test:** After adding any button, visually verify the label is readable against its background. Do not skip this for "obviously styled" components.
