import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  computed,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConversationService } from '../../core/services/conversation.service';
import { ChatWsService } from '../../core/services/chat-ws.service';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; flex-shrink: 0; }

    .input-bar {
      padding: 10px 16px 12px;
      border-top: 1px solid var(--color-border);
      background: var(--color-canvas);
    }

    .model-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .spacer { flex: 1; }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
      transition: background 0.3s;
    }

    .status-dot.connected    { background: var(--color-success); }
    .status-dot.disconnected { background: var(--color-error); }

    .status-label {
      font-size: 10px;
      color: var(--color-text-tertiary);
      white-space: nowrap;
      font-family: var(--font-mono);
      letter-spacing: 0.02em;
    }

    .input-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
    }

    /* CHANGED: frosted glass, borderless until focus, Apple ease [Phase 6] */
    .textarea {
      flex: 1;
      resize: none;
      background: var(--color-glass-bg);
      -webkit-backdrop-filter: blur(10px) saturate(1.4);
      backdrop-filter: blur(10px) saturate(1.4);
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 9px 13px;
      font-size: var(--text-base);
      font-family: var(--font-sans);
      color: var(--color-text-primary);
      line-height: 1.55;
      outline: none;
      transition: border-color var(--duration-fast) var(--ease),
                  box-shadow    var(--duration-fast) var(--ease),
                  background    var(--duration-fast) var(--ease);
    }

    .textarea::placeholder {
      color: var(--color-text-tertiary);
      font-family: var(--font-mono);
      font-size: var(--text-sm);
    }

    .textarea:focus {
      border-color: var(--color-accent);
      background: var(--color-surface);
      box-shadow: 0 0 0 3px var(--color-accent-subtle);
    }

    .textarea:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .send-btn {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background var(--duration-fast) var(--ease),
                  box-shadow  var(--duration-fast) var(--ease),
                  transform   var(--duration-fast) var(--ease),
                  opacity     var(--duration-fast) var(--ease);
      outline: none;
      padding: 0;
    }

    .send-btn.active {
      background: var(--color-accent);
      box-shadow: 0 2px 10px var(--color-accent-subtle);
    }

    .send-btn.active:hover {
      background: var(--color-accent-hover);
      box-shadow: 0 2px 14px color-mix(in srgb, var(--color-accent) 30%, transparent);
    }

    .send-btn.active:active { transform: scale(0.94); }

    .send-btn.inactive {
      background: var(--color-surface-active);
      cursor: not-allowed;
      opacity: 0.5;
    }

    .send-btn svg { width: 15px; height: 15px; }
    .send-btn.active  svg { stroke: var(--color-canvas); }
    .send-btn.inactive svg { stroke: var(--color-text-tertiary); }

    .hint {
      margin-top: 6px;
      text-align: center;
      font-size: 10.5px;
      color: var(--color-text-tertiary);
      font-family: var(--font-mono);
      letter-spacing: 0.03em;
    }

    @keyframes spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }

    .spinning { animation: spin 0.8s linear infinite; }
  `],
  template: `
    <div class="input-bar">
      <div class="model-row">
        <div class="spacer"></div>
        <div class="status-indicator">
          <div
            class="status-dot"
            [class.connected]="ws.connected()"
            [class.disconnected]="!ws.connected()"
          ></div>
          <span class="status-label">{{ ws.connected() ? 'connected' : 'reconnecting' }}</span>
        </div>
      </div>

      <div class="input-row">
        <textarea
          #inputRef
          class="textarea"
          rows="1"
          placeholder="SELECT * FROM your_question…"
          [disabled]="isDisabled()"
          [(ngModel)]="draft"
          (keydown)="onKeyDown($event)"
          (input)="autoResize()"
        ></textarea>

        <button
          class="send-btn"
          [class.active]="canSend()"
          [class.inactive]="!canSend()"
          [disabled]="!canSend()"
          (click)="submit()"
          title="Send (Enter)"
        >
          @if (conversations.streaming()) {
            <svg class="spinning" viewBox="0 0 24 24" fill="none" stroke-width="2.5" stroke-linecap="round">
              <path d="M12 2a10 10 0 0 1 10 10" stroke="var(--color-text-tertiary)"/>
            </svg>
          } @else {
            <svg fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          }
        </button>
      </div>

      <p class="hint">enter ↵ send · shift+enter new line</p>
    </div>
  `,
})
export class ChatInputComponent implements OnInit {
  @ViewChild('inputRef') inputRef!: ElementRef<HTMLTextAreaElement>;

  readonly conversations = inject(ConversationService);
  readonly ws = inject(ChatWsService);

  protected draft = '';

  protected readonly isDisabled = computed(
    () => this.conversations.streaming() || !this.ws.connected(),
  );

  protected readonly canSend = computed(
    () => this.draft.trim().length > 0 && !this.isDisabled(),
  );

  ngOnInit(): void {
    if (!this.conversations.activeConversation()) {
      this.conversations.newConversation();
    }
    this.ws.connect();
  }

  protected onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.submit();
    }
  }

  protected submit(): void {
    const text = this.draft.trim();
    if (!text || this.isDisabled()) return;
    this.draft = '';
    this.resetTextareaHeight();
    this.conversations.sendMessage(text);
  }

  protected autoResize(): void {
    const el = this.inputRef?.nativeElement;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }

  private resetTextareaHeight(): void {
    const el = this.inputRef?.nativeElement;
    if (el) el.style.height = 'auto';
  }
}
