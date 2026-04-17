import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConversationService } from '../../core/services/conversation.service';
import { ProvidersService } from '../../core/services/providers.service';
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

    .model-label {
      font-size: 10px;
      font-weight: 500;
      color: var(--color-text-tertiary);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
      font-family: var(--font-mono);
    }

    .model-select {
      flex: 1;
      max-width: 280px;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      color: var(--color-text-primary);
      font-size: 12px;
      font-family: var(--font-mono);
      border-radius: 5px;
      padding: 4px 28px 4px 9px;
      outline: none;
      cursor: pointer;
      transition: border-color 0.15s;
      appearance: none;
      -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%237892AC' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 9px center;
    }

    .model-select:focus { border-color: var(--color-accent); }
    .model-select option, .model-select optgroup {
      background: var(--color-surface);
      color: var(--color-text-primary);
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

    .textarea {
      flex: 1;
      resize: none;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      padding: 9px 13px;
      font-size: 13.5px;
      font-family: var(--font-sans);
      color: var(--color-text-primary);
      line-height: 1.55;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }

    .textarea::placeholder {
      color: var(--color-text-tertiary);
      font-family: var(--font-mono);
      font-size: 12.5px;
    }

    .textarea:focus {
      border-color: var(--color-accent);
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
      transition: background 0.15s, box-shadow 0.15s, transform 0.1s, opacity 0.15s;
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
      @if (providers.hasProviders()) {
        <div class="model-row">
          <span class="model-label">model</span>
          <select
            class="model-select"
            [value]="selectedModel()"
            (change)="onModelChange($event)"
          >
            @for (group of providers.providerGroups(); track group.provider) {
              <optgroup [label]="group.label">
                @for (model of group.models; track model) {
                  <option [value]="model">{{ model }}</option>
                }
              </optgroup>
            }
          </select>

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
      }

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
  readonly providers = inject(ProvidersService);
  readonly ws = inject(ChatWsService);

  protected draft = '';

  protected readonly selectedModel = this.providers.selectedModel;

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

  protected onModelChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.providers.selectModel(target.value);
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
