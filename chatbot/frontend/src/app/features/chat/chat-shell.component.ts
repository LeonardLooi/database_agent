import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { ConversationService } from '../../core/services/conversation.service';
import { ChatWsService } from '../../core/services/chat-ws.service';
import { ThemeService } from '../../core/services/theme.service';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { ChatWindowComponent } from './chat-window.component';
import { ChatInputComponent } from './chat-input.component';
import { ModelSelectorComponent } from './components/model-selector.component';

@Component({
  selector: 'app-chat-shell',
  standalone: true,
  imports: [SidebarComponent, ChatWindowComponent, ChatInputComponent, ModelSelectorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host {
      display: flex;
      height: 100vh;
      overflow: hidden;
      background: var(--color-canvas);
      font-family: var(--font-sans);
    }

    .main-area {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
      overflow: hidden;
    }

    .top-bar {
      display: flex;
      align-items: center;
      padding: 0 16px 0 20px;
      height: 49px;
      border-bottom: 1px solid var(--color-border);
      background: var(--color-canvas);
      flex-shrink: 0;
      gap: 10px;
    }

    .conv-title {
      flex: 1;
      font-size: 12px;
      font-weight: 500;
      color: var(--color-text-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      letter-spacing: 0.01em;
      font-family: var(--font-mono);
    }

    /* CHANGED: Apple ease on hover transitions [Phase 6] */
    .theme-toggle {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border-radius: 7px;
      border: 1px solid var(--color-border);
      background: transparent;
      cursor: pointer;
      color: var(--color-text-secondary);
      flex-shrink: 0;
      transition: background var(--duration-fast) var(--ease),
                  border-color var(--duration-fast) var(--ease),
                  color var(--duration-fast) var(--ease);
      padding: 0;
    }

    .theme-toggle:hover {
      background: var(--color-surface-hover);
      border-color: var(--color-border-strong);
      color: var(--color-text-primary);
    }

    .theme-toggle svg {
      width: 15px;
      height: 15px;
    }
  `],
  template: `
    <app-sidebar />

    <div class="main-area">
      <div class="top-bar">
        <span class="conv-title">{{ activeTitle() }}</span>

        <app-model-selector />

        <button
          class="theme-toggle"
          (click)="toggleTheme()"
          [title]="theme.isDark() ? 'Switch to light mode' : 'Switch to dark mode'"
          [attr.aria-label]="theme.isDark() ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          @if (theme.isDark()) {
            <!-- Sun icon for light mode switch -->
            <svg fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          } @else {
            <!-- Moon icon for dark mode switch -->
            <svg fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          }
        </button>
      </div>

      <app-chat-window />
      <app-chat-input />
    </div>
  `,
})
export class ChatShellComponent implements OnInit {
  private readonly conversations = inject(ConversationService);
  private readonly ws = inject(ChatWsService);
  protected readonly theme = inject(ThemeService);

  protected activeTitle(): string {
    return this.conversations.activeConversation()?.title ?? 'New conversation';
  }

  protected toggleTheme(): void {
    // Brief class to enable smooth cross-component transitions during switch
    document.documentElement.classList.add('theme-switching');
    this.theme.toggle();
    setTimeout(() => document.documentElement.classList.remove('theme-switching'), 300);
  }

  async ngOnInit(): Promise<void> {
    this.ws.connect();
    await this.conversations.loadHistory();
    if (!this.conversations.activeConversation()) {
      this.conversations.newConversation();
    }
  }
}
