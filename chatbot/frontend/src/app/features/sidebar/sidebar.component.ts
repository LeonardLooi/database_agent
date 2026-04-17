import {
  ChangeDetectionStrategy,
  Component,
  HostBinding,
  inject,
  signal,
} from '@angular/core';
import { ConversationService } from '../../core/services/conversation.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      flex-shrink: 0;
      background: var(--color-surface);
      border-right: 1px solid var(--color-border);
      font-family: var(--font-sans);
      overflow: hidden;
      transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ── Shared header row ── */
    .header {
      display: flex;
      align-items: center;
      height: 49px;
      border-bottom: 1px solid var(--color-border);
      flex-shrink: 0;
      padding: 0 11px;
      gap: 8px;
      overflow: hidden;
    }

    /* Collapsed header: full row is the click target */
    .header-collapsed {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      height: 49px;
      border-bottom: 1px solid var(--color-border);
      flex-shrink: 0;
      cursor: pointer;
      border: none;
      background: transparent;
      width: 100%;
      padding: 0;
      color: var(--color-text-tertiary);
      transition: background 0.15s, color 0.15s;
      font-family: var(--font-sans);
      border-bottom: 1px solid var(--color-border);
    }

    .header-collapsed:hover {
      background: var(--color-surface-hover);
      color: var(--color-accent);
    }

    .header-collapsed svg { width: 16px; height: 16px; stroke: currentColor; }

    .expand-hint {
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: inherit;
      line-height: 1;
    }

    .logo-mark {
      width: 26px;
      height: 26px;
      min-width: 26px;
      border-radius: 7px;
      background: var(--color-accent);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .logo-mark svg { width: 13px; height: 13px; fill: white; }

    .app-name {
      flex: 1;
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text-primary);
      letter-spacing: -0.01em;
      white-space: nowrap;
      overflow: hidden;
    }

    /* Collapse button — in expanded header */
    .toggle-btn {
      width: 26px;
      min-width: 26px;
      height: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      border: none;
      background: transparent;
      color: var(--color-text-tertiary);
      cursor: pointer;
      transition: background 0.12s, color 0.12s;
      padding: 0;
    }

    .toggle-btn:hover {
      background: var(--color-surface-active);
      color: var(--color-text-secondary);
    }

    .toggle-btn svg { width: 14px; height: 14px; stroke: currentColor; }

    /* ── New chat area ── */
    .new-chat-area {
      padding: 10px 10px 6px;
      flex-shrink: 0;
      display: flex;
      justify-content: center;
    }

    /* Expanded: full-width labelled button */
    .new-chat-btn {
      width: 100%;
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 7px 11px;
      border-radius: 7px;
      border: 1px solid var(--color-border-strong);
      background: var(--color-canvas);
      color: var(--color-text-secondary);
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.12s, border-color 0.12s, color 0.12s;
      font-family: var(--font-sans);
      white-space: nowrap;
    }

    .new-chat-btn:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .new-chat-btn svg { width: 13px; height: 13px; flex-shrink: 0; stroke: currentColor; }

    /* Collapsed: square bubble that fills the 48px strip */
    .new-chat-bubble {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      border: none;
      background: var(--color-accent);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-accent) 40%, transparent);
      transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
      padding: 0;
    }

    .new-chat-bubble:hover {
      background: var(--color-accent-hover);
      transform: scale(1.06);
      box-shadow: 0 4px 12px color-mix(in srgb, var(--color-accent) 50%, transparent);
    }

    .new-chat-bubble:active { transform: scale(0.95); }
    .new-chat-bubble svg { width: 16px; height: 16px; stroke: white; }

    /* ── Section label ── */
    .section-label {
      padding: 10px 14px 3px;
      font-size: 9.5px;
      font-weight: 500;
      color: var(--color-text-tertiary);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      flex-shrink: 0;
      white-space: nowrap;
      font-family: var(--font-mono);
    }

    /* ── Conversation list ── */
    .conv-list {
      flex: 1;
      overflow-y: auto;
      padding: 2px 6px 12px;
    }

    .conv-list::-webkit-scrollbar { width: 3px; }
    .conv-list::-webkit-scrollbar-track { background: transparent; }
    .conv-list::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 2px; }

    .conv-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 9px;
      border-radius: 5px;
      cursor: pointer;
      margin-bottom: 1px;
      transition: background 0.1s, border-color 0.1s;
      color: var(--color-text-secondary);
      font-size: 12px;
      font-family: var(--font-sans);
      position: relative;
      border-left: 2px solid transparent;
    }

    .conv-item:hover {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }
    .conv-item.active {
      background: var(--color-surface-active);
      color: var(--color-text-primary);
      font-weight: 500;
      border-left-color: var(--color-accent);
    }
    .conv-item svg { width: 12px; height: 12px; flex-shrink: 0; stroke: currentColor; opacity: 0.5; }

    .conv-title {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .delete-btn {
      display: none;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border-radius: 4px;
      border: none;
      background: transparent;
      cursor: pointer;
      color: var(--color-text-tertiary);
      flex-shrink: 0;
      padding: 0;
      transition: background 0.1s, color 0.1s;
    }

    .delete-btn svg { width: 11px; height: 11px; stroke: currentColor; }
    .conv-item:hover .delete-btn { display: flex; }
    .delete-btn:hover { background: var(--color-error-bg); color: var(--color-error); }

    .empty-state {
      padding: 20px 14px;
      text-align: center;
      color: var(--color-text-tertiary);
      font-size: 12px;
      line-height: 1.6;
    }
  `],
  template: `
    @if (collapsed()) {
      <!-- Collapsed header: entire row is one large click target -->
      <button class="header-collapsed" (click)="toggle()" title="Expand sidebar">
        <svg fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <polyline points="13 17 18 12 13 7"/>
          <polyline points="6 17 11 12 6 7"/>
        </svg>
        <span class="expand-hint">Expand</span>
      </button>
    } @else {
      <!-- Expanded header: logo + name + collapse button -->
      <div class="header">
        <div class="logo-mark">
          <svg viewBox="0 0 20 20">
            <ellipse cx="10" cy="5" rx="7" ry="2.5"/>
            <path d="M3 5v4c0 1.38 3.13 2.5 7 2.5s7-1.12 7-2.5V5"/>
            <path d="M3 9v4c0 1.38 3.13 2.5 7 2.5s7-1.12 7-2.5V9" opacity="0.6"/>
          </svg>
        </div>
        <span class="app-name">Database Agent</span>
        <button class="toggle-btn" (click)="toggle()" title="Collapse sidebar">
          <svg fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M9 3v18"/>
          </svg>
        </button>
      </div>
    }

    <!-- New chat: full button when expanded, bubble when collapsed -->
    <div class="new-chat-area">
      @if (collapsed()) {
        <button class="new-chat-bubble" (click)="newChat()" title="New conversation">
          <svg fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      } @else {
        <button class="new-chat-btn" (click)="newChat()">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New conversation
        </button>
      }
    </div>

    <!-- Conversation list: hidden when collapsed -->
    @if (!collapsed()) {
      @if (conversations.conversations().length > 0) {
        <div class="section-label">Recent</div>
      }

      <div class="conv-list">
        @if (conversations.conversations().length === 0) {
          <div class="empty-state">No conversations yet.<br>Start one above.</div>
        }
        @for (conv of conversations.conversations(); track conv.id) {
          <div
            class="conv-item"
            [class.active]="conv.id === conversations.activeId()"
            (click)="conversations.selectConversation(conv.id)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            <span class="conv-title">{{ conv.title }}</span>
            <button class="delete-btn" (click)="deleteConv($event, conv.id)" title="Delete">
              <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
                <path d="M10 11v6"/><path d="M14 11v6"/>
              </svg>
            </button>
          </div>
        }
      </div>
    }
  `,
})
export class SidebarComponent {
  readonly conversations = inject(ConversationService);
  readonly collapsed = signal(false);

  @HostBinding('style.width')
  get hostWidth(): string { return this.collapsed() ? '48px' : '240px'; }

  toggle(): void { this.collapsed.update(v => !v); }

  newChat(): void { this.conversations.newConversation(); }

  deleteConv(event: MouseEvent, id: string): void {
    event.stopPropagation();
    this.conversations.deleteConversation(id);
  }
}
