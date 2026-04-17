# A2UI Renderer & Chat Component Templates

## Renderer Component

```typescript
// components/a2ui-renderer/a2ui-renderer.component.ts

import { Component, computed, inject, input, output } from '@angular/core';
import { A2UIComponentDef, A2UIValue, SurfaceState, UserAction } from '../../models/a2ui.model';
import { A2UICatalogService } from '../../services/a2ui-catalog.service';
import { A2UISanitizerService } from '../../services/a2ui-sanitizer.service';

@Component({
  selector: 'app-a2ui-renderer',
  standalone: true,
  imports: [A2UIRendererComponent],
  template: `
    @let comp = getComponent();
    @if (comp) {
      @switch (comp.type) {

        @case ('Column') {
          <div class="flex flex-col gap-2" [class.items-center]="comp.alignment === 'center'"
               [class.items-start]="comp.alignment === 'start'" [class.items-end]="comp.alignment === 'end'">
            @for (childId of explicitChildIds(); track childId) {
              <app-a2ui-renderer [surface]="surface()" [componentId]="childId"
                (actionTriggered)="actionTriggered.emit($event)" />
            }
          </div>
        }

        @case ('Row') {
          <div class="flex flex-row gap-2 flex-wrap" [class.justify-center]="comp.alignment === 'center'"
               [class.justify-start]="comp.alignment === 'start'" [class.justify-end]="comp.alignment === 'end'">
            @for (childId of explicitChildIds(); track childId) {
              <app-a2ui-renderer [surface]="surface()" [componentId]="childId"
                (actionTriggered)="actionTriggered.emit($event)" />
            }
          </div>
        }

        @case ('Card') {
          <div class="card bg-base-100 shadow-md mb-4">
            <div class="card-body">
              @if (comp.child) {
                <app-a2ui-renderer [surface]="surface()" [componentId]="comp.child"
                  (actionTriggered)="actionTriggered.emit($event)" />
              }
            </div>
          </div>
        }

        @case ('Text') {
          @switch (comp.usageHint) {
            @case ('h1') { <h1 class="text-4xl font-bold">{{ resolveText(comp.text) }}</h1> }
            @case ('h2') { <h2 class="text-3xl font-bold">{{ resolveText(comp.text) }}</h2> }
            @case ('h3') { <h3 class="text-2xl font-semibold">{{ resolveText(comp.text) }}</h3> }
            @case ('h4') { <h4 class="text-xl font-semibold">{{ resolveText(comp.text) }}</h4> }
            @case ('h5') { <h5 class="text-lg font-medium">{{ resolveText(comp.text) }}</h5> }
            @case ('h6') { <h6 class="text-base font-medium">{{ resolveText(comp.text) }}</h6> }
            @case ('caption') { <p class="text-sm text-base-content/60">{{ resolveText(comp.text) }}</p> }
            @default { <p>{{ resolveText(comp.text) }}</p> }
          }
        }

        @case ('Image') {
          <img [src]="safeUrl(comp.url)" alt="" class="rounded-lg max-w-full" />
        }

        @case ('Icon') {
          <span class="material-icons">{{ resolveText(comp.name) }}</span>
        }

        @case ('Button') {
          <button [class]="comp.primary ? 'btn btn-primary' : 'btn'"
                  (click)="onAction(comp, componentId())">
            @if (comp.child) {
              <app-a2ui-renderer [surface]="surface()" [componentId]="comp.child"
                (actionTriggered)="actionTriggered.emit($event)" />
            }
          </button>
        }

        @case ('TextField') {
          <label class="form-control w-full">
            @if (comp.label) {
              <div class="label"><span class="label-text">{{ resolveText(comp.label) }}</span></div>
            }
            @if (comp.textFieldType === 'longText') {
              <textarea class="textarea textarea-bordered w-full"></textarea>
            } @else {
              <input class="input input-bordered w-full"
                     [type]="comp.textFieldType === 'email' ? 'email' : 'text'"
                     [placeholder]="resolveText(comp.label)" />
            }
          </label>
        }

        @case ('Checkbox') {
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" class="checkbox" />
            <span>{{ resolveText(comp.label) }}</span>
          </label>
        }

        @case ('DateTimeInput') {
          <input class="input input-bordered"
                 [type]="comp.enableDate && comp.enableTime ? 'datetime-local' : comp.enableDate ? 'date' : 'time'" />
        }

        @case ('Divider') {
          @if (comp.axis === 'vertical') {
            <div class="divider divider-horizontal"></div>
          } @else {
            <div class="divider"></div>
          }
        }

        @case ('List') {
          <ul class="menu bg-base-200 rounded-box">
            @for (childId of explicitChildIds(); track childId) {
              <li>
                <app-a2ui-renderer [surface]="surface()" [componentId]="childId"
                  (actionTriggered)="actionTriggered.emit($event)" />
              </li>
            }
          </ul>
        }

        @case ('Tabs') {
          <div role="tablist" class="tabs tabs-boxed">
            @for (tab of asTabs(comp); track tab.child) {
              <a role="tab" class="tab">{{ resolveText(tab.title) }}</a>
            }
          </div>
        }

        @case ('Modal') {
          @if (comp.entryPointChild) {
            <app-a2ui-renderer [surface]="surface()" [componentId]="comp.entryPointChild"
              (actionTriggered)="actionTriggered.emit($event)" />
          }
        }

      }
    }
  `,
})
export class A2UIRendererComponent {
  surface = input.required<SurfaceState>();
  componentId = input.required<string>();
  actionTriggered = output<UserAction>();

  private catalog = inject(A2UICatalogService);
  private sanitizer = inject(A2UISanitizerService);

  getComponent = computed(() => {
    const comp = this.surface().componentMap.get(this.componentId());
    if (!comp) return null;
    if (!this.catalog.isAllowed(comp.type)) {
      console.warn(`A2UI: Rejected unknown component type: ${comp.type}`);
      return null;
    }
    return comp;
  });

  // For Row, Column, List: children via explicitList
  explicitChildIds = computed(() => {
    const comp = this.getComponent();
    if (!comp?.children) return [];
    return 'explicitList' in comp.children ? comp.children.explicitList : [];
  });

  resolveText(value: A2UIValue | undefined): string {
    if (!value) return '';
    if ('path' in value) {
      const data = this.surface().dataModel[value.path as string];
      if (data != null) return this.sanitizer.sanitizeText(String(data));
      // Fall back to literalString default if path resolves to nothing
      if ('literalString' in value) return this.sanitizer.sanitizeText(value.literalString as string);
      return '';
    }
    if ('literalString' in value) return this.sanitizer.sanitizeText(value.literalString as string);
    return '';
  }

  safeUrl(value: A2UIValue | undefined): string {
    const text = value && 'literalString' in value ? (value.literalString as string) : '';
    return this.sanitizer.sanitizeUrl(text);
  }

  asTabs(comp: A2UIComponentDef): Array<{ title: A2UIValue; child: string }> {
    return Array.isArray(comp.tabItems) ? comp.tabItems as Array<{ title: A2UIValue; child: string }> : [];
  }

  onAction(comp: A2UIComponentDef, componentId: string): void {
    if (!comp.action?.name) return;
    const action = comp.action;
    this.actionTriggered.emit({
      name: action.name,
      surfaceId: this.surface().surfaceId,
      sourceComponentId: componentId,
      timestamp: new Date().toISOString(),
      context: Object.fromEntries(
        (action.context ?? []).map(c => [c.key, this.resolveActionValue(c.value)]),
      ),
    });
  }

  private resolveActionValue(value: A2UIValue): unknown {
    if ('path' in value) return this.surface().dataModel[value.path as string];
    if ('literalString' in value) return value.literalString;
    return null;
  }
}
```

> Chat page component, streaming variant, and wire format reference are in `a2ui-chat-template.md`.
