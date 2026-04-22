import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatMessage } from '../models/chat.models';
import { RoutingBadgeComponent } from './routing-badge.component';

const PROVIDER_DISPLAY: Record<string, string> = {
  anthropic: 'Claude',
  openai:    'GPT',
  gemini:    'Gemini',
  aws:       'Nova',
};

const PROVIDER_INITIAL: Record<string, string> = {
  anthropic: 'C',
  openai:    'G',
  gemini:    'G',
  aws:       'N',
};

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [CommonModule, RoutingBadgeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; width: 100%; }

    /* CHANGED: Apple ease on animations, system font sizes [Phase 6] */
    @keyframes msg-enter {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes cursor-blink {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0; }
    }

    .message-row {
      display: flex;
      width: 100%;
      margin-bottom: 20px;
      padding: 0 24px;
      align-items: flex-start;
      animation: msg-enter 0.18s ease-out both;
    }

    .message-row.user      { justify-content: flex-end; }
    .message-row.assistant { justify-content: flex-start; }

    /* AI avatar — amber square */
    .ai-avatar {
      width: 28px;
      height: 28px;
      min-width: 28px;
      border-radius: 7px;
      background: var(--color-accent);
      color: var(--color-canvas);
      font-size: 11px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-right: 10px;
      margin-top: 2px;
      font-family: var(--font-mono);
      letter-spacing: -0.03em;
    }

    .bubble-col {
      display: flex;
      flex-direction: column;
      max-width: 70%;
    }

    .message-row.user .bubble-col { align-items: flex-end; }

    /* User bubble — clean dark pill */
    .bubble.user {
      padding: 10px 15px;
      border-radius: 14px;
      border-bottom-right-radius: 3px;
      font-size: 13.5px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-words;
      font-family: var(--font-sans);
      background: var(--color-bubble-user-bg);
      color: var(--color-bubble-user-text);
      border: 1px solid transparent;
    }

    /* AI bubble — monospace, left amber accent */
    .bubble.assistant {
      padding: 11px 15px;
      border-radius: 4px 14px 14px 14px;
      font-size: 13px;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-words;
      font-family: var(--font-mono);
      background: var(--color-bubble-ai-bg);
      color: var(--color-bubble-ai-text);
      border: 1px solid var(--color-bubble-ai-border);
      border-left: 2px solid var(--color-accent);
    }

    .bubble.error {
      padding: 11px 15px;
      border-radius: 4px 14px 14px 14px;
      font-size: 13px;
      line-height: 1.65;
      font-family: var(--font-mono);
      background: var(--color-error-bg);
      color: var(--color-error-text);
      border: 1px solid var(--color-error-border);
      border-left: 2px solid var(--color-error);
    }

    /* Terminal cursor blink — replaces bouncing dots */
    .cursor-blink {
      display: inline-block;
      width: 7px;
      height: 1em;
      background: var(--color-accent);
      animation: cursor-blink 0.85s step-end infinite;
      vertical-align: text-bottom;
      border-radius: 1px;
    }

    /* Footer */
    .bubble-footer {
      margin-top: 5px;
      padding: 0 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .meta {
      font-size: 10px;
      color: var(--color-text-tertiary);
      font-family: var(--font-mono);
      letter-spacing: 0.02em;
    }

    .meta-sep {
      font-size: 10px;
      color: var(--color-border-strong);
      font-family: var(--font-mono);
    }

    /* Clarification candidate buttons */
    .clarification-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 10px;
    }

    .clarification-btn {
      padding: 7px 13px;
      border-radius: 6px;
      border: 1px solid var(--color-accent);
      background: transparent;
      color: var(--color-accent);
      font-size: 12px;
      font-family: var(--font-mono);
      letter-spacing: 0.01em;
      cursor: pointer;
      text-align: left;
      transition: background 0.12s, color 0.12s;
    }

    .clarification-btn:hover:not([disabled]) {
      background: var(--color-accent);
      color: var(--color-canvas);
    }

    .clarification-btn[disabled],
    .clarification-btn.answered {
      border-color: var(--color-border-strong);
      color: var(--color-text-tertiary);
      cursor: not-allowed;
      opacity: 0.55;
    }
  `],
  template: `
    <div class="message-row" [class.user]="message().role === 'user'" [class.assistant]="message().role === 'assistant'">

      @if (message().role === 'assistant') {
        <div class="ai-avatar">{{ providerInitial() }}</div>
      }

      <div class="bubble-col">
        <div
          class="bubble"
          [class.user]="message().role === 'user'"
          [class.assistant]="message().role === 'assistant' && !message().error"
          [class.error]="!!message().error"
        >
          @if (message().streaming) {
            @if (message().content) {
              {{ message().content }}<span class="cursor-blink"></span>
            } @else {
              <span class="cursor-blink"></span>
            }
          } @else {
            {{ message().content }}
          }
        </div>

        @if (message().role === 'assistant' && !message().streaming && message().provider) {
          <div class="bubble-footer">
            <span class="meta">{{ providerLabel() }}</span>
            <span class="meta-sep">/</span>
            <span class="meta">{{ modelShort() }}</span>
            @if (message().tokenCount) {
              <span class="meta-sep">·</span>
              <span class="meta">{{ message().tokenCount }}t</span>
            }
            @if (message().routingMetadata) {
              <app-routing-badge [meta]="message().routingMetadata" />
            }
          </div>
        }

        @if (message().clarification) {
          <div class="clarification-box">
            @for (c of message().clarification!.candidates; track c) {
              <button
                class="clarification-btn"
                [disabled]="message().clarification!.answered"
                [class.answered]="message().clarification!.answered"
                (click)="selectCandidate.emit(c)"
              >{{ c }}</button>
            }
          </div>
        }
      </div>

    </div>
  `,
})
export class MessageBubbleComponent {
  readonly message = input.required<ChatMessage>();
  readonly selectCandidate = output<string>();

  readonly providerLabel = computed(() => {
    const p = this.message().provider ?? '';
    return PROVIDER_DISPLAY[p] ?? p;
  });

  readonly providerInitial = computed(() => {
    const p = this.message().provider ?? '';
    return PROVIDER_INITIAL[p] ?? (p[0]?.toUpperCase() ?? 'AI');
  });

  readonly modelShort = computed(() => {
    const m = this.message().model ?? '';
    // AWS: "amazon.nova-lite-v1:0" → "nova-lite"
    if (m.startsWith('amazon.')) {
      const inner = m.replace('amazon.', '').replace(/-v\d+:\d+$/, '');
      return inner;
    }
    const parts = m.split('-');
    if (parts.length > 3) return parts.slice(1, 3).join('-');
    return m;
  });
}
