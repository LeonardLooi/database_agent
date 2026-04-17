# A2UI Angular — Agent Service and Unit Tests

## Agent Service (REST + SSE)

```typescript
// services/a2ui-agent.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { map } from 'rxjs/operators';
import {
  A2UIMessage, SurfaceState, UserAction,
  A2UIComponentDef, DataModelContentsEntry,
} from '../models/a2ui.model';

@Injectable({ providedIn: 'root' })
export class A2UIAgentService {
  private http = inject(HttpClient);

  sendMessage(message: string): Observable<SurfaceState> {
    return this.http.post<A2UIMessage[]>('/api/agent/chat', { message }).pipe(
      map(messages => this.buildSurfaceState(messages)),
    );
  }

  sendUserAction(action: UserAction): Observable<SurfaceState> {
    return this.http.post<A2UIMessage[]>('/api/agent/action', action).pipe(
      map(messages => this.buildSurfaceState(messages)),
    );
  }

  streamMessages(message: string): Observable<A2UIMessage> {
    const subject = new Subject<A2UIMessage>();
    const eventSource = new EventSource(
      `/api/agent/stream?message=${encodeURIComponent(message)}`,
    );
    eventSource.onmessage = (event) => {
      try {
        const line = (event.data as string).trim();
        if (line) subject.next(JSON.parse(line) as A2UIMessage);
      } catch (e) {
        console.error('A2UI: Failed to parse JSONL message', e);
      }
    };
    eventSource.addEventListener('done', () => { subject.complete(); eventSource.close(); });
    eventSource.onerror = () => {
      console.error('A2UI: SSE stream error');
      subject.complete();
      eventSource.close();
    };
    return subject.asObservable();
  }

  // Folds a sequence of JSONL protocol messages into a single SurfaceState
  buildSurfaceState(messages: A2UIMessage[]): SurfaceState {
    const state: SurfaceState = {
      surfaceId: '',
      componentMap: new Map(),
      rootComponentId: '',
      dataModel: {},
    };
    for (const msg of messages) {
      if (msg.surfaceUpdate) {
        state.surfaceId = msg.surfaceUpdate.surfaceId;
        // Build map from ARRAY (official format)
        for (const entry of msg.surfaceUpdate.components) {
          state.componentMap.set(entry.id, entry.component);
        }
      }
      if (msg.dataModelUpdate) {
        const base = msg.dataModelUpdate.path ?? '';
        for (const entry of msg.dataModelUpdate.contents) {
          const fullKey = base ? `${base}/${entry.key}` : entry.key;
          if ('valueString' in entry) state.dataModel[fullKey] = entry.valueString;
          else if ('valueNumber' in entry) state.dataModel[fullKey] = entry.valueNumber;
          else if ('valueMap' in entry) state.dataModel[fullKey] = entry.valueMap;
        }
      }
      if (msg.beginRendering) {
        state.surfaceId = msg.beginRendering.surfaceId;
        state.rootComponentId = msg.beginRendering.root;  // field is 'root', not 'rootComponent'
      }
      // deleteSurface: handled at the chat component level, not here
    }

    // Gemini resilience: if agent sent surfaceUpdate with a 'root' component but
    // omitted beginRendering, auto-set rootComponentId so the renderer doesn't silently show nothing.
    if (!state.rootComponentId && state.componentMap.has('root')) {
      state.rootComponentId = 'root';
    }

    return state;
  }
}
```

---

## Unit Test Template

```typescript
// components/a2ui-renderer/a2ui-renderer.component.spec.ts

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { A2UIRendererComponent } from './a2ui-renderer.component';
import { SurfaceState, UserAction } from '../../models/a2ui.model';

function makeSurface(overrides: Partial<SurfaceState> = {}): SurfaceState {
  return {
    surfaceId: 'main',
    componentMap: new Map(),
    rootComponentId: 'root',
    dataModel: {},
    ...overrides,
  };
}

describe('A2UIRendererComponent', () => {
  let fixture: ComponentFixture<A2UIRendererComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [A2UIRendererComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(A2UIRendererComponent);
  });

  it('should render a Card with a Text child', () => {
    const surface = makeSurface({
      componentMap: new Map([
        ['root', { type: 'Card', child: 'text-1' }],
        ['text-1', { type: 'Text', text: { literalString: 'Hello World' }, usageHint: 'body' }],
      ]),
    });
    fixture.componentRef.setInput('surface', surface);
    fixture.componentRef.setInput('componentId', 'root');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Hello World');
  });

  it('should skip unknown component types', () => {
    const surface = makeSurface({
      componentMap: new Map([
        ['root', { type: 'malicious-script' }],
      ]),
    });
    fixture.componentRef.setInput('surface', surface);
    fixture.componentRef.setInput('componentId', 'root');
    fixture.detectChanges();
    expect(fixture.nativeElement.innerHTML).not.toContain('malicious-script');
    expect(fixture.nativeElement.children.length).toBe(0);
  });

  it('should emit UserAction with resolved context on button click', () => {
    const surface = makeSurface({
      componentMap: new Map([
        ['btn-book', {
          type: 'Button',
          label: { literalString: 'Book' },
          action: {
            name: 'book_hotel',
            context: [{ key: 'hotelId', value: { literalString: 'H-456' } }],
          },
        }],
      ]),
      dataModel: {},
    });
    fixture.componentRef.setInput('surface', surface);
    fixture.componentRef.setInput('componentId', 'btn-book');
    fixture.detectChanges();

    let emitted: UserAction | undefined;
    fixture.componentInstance.actionTriggered.subscribe(a => (emitted = a));
    fixture.nativeElement.querySelector('button').click();

    expect(emitted).toMatchObject({
      name: 'book_hotel',
      surfaceId: 'main',
      sourceComponentId: 'btn-book',
      context: { hotelId: 'H-456' },
    });
    expect(emitted?.timestamp).toBeTruthy();
  });

  it('should resolve Text content from dataModel via path binding', () => {
    const surface = makeSurface({
      componentMap: new Map([
        ['root', {
          type: 'Text',
          text: { path: '/reservation/date' },
          usageHint: 'body',
        }],
      ]),
      dataModel: { '/reservation/date': '2026-04-01' },
    });
    fixture.componentRef.setInput('surface', surface);
    fixture.componentRef.setInput('componentId', 'root');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('2026-04-01');
  });

  it('should use literalString default when path resolves to nothing', () => {
    const surface = makeSurface({
      componentMap: new Map([
        ['root', {
          type: 'Text',
          text: { path: '/reservation/missing', literalString: 'N/A' },
          usageHint: 'body',
        }],
      ]),
      dataModel: {},
    });
    fixture.componentRef.setInput('surface', surface);
    fixture.componentRef.setInput('componentId', 'root');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('N/A');
  });
});
```
