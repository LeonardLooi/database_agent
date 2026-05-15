import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatMessage, MessageAttachment } from '../models/chat.models';
import { RoutingBadgeComponent } from './routing-badge.component';
import { MarkdownService } from '../../core/services/markdown.service';

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

    /* User bubble — plain text, dark pill */
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

    /* AI bubble — markdown content, left accent border */
    .bubble.assistant {
      padding: 11px 15px;
      border-radius: 4px 14px 14px 14px;
      font-size: 13px;
      line-height: 1.65;
      word-break: break-words;
      font-family: var(--font-sans);
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

    /* Streaming cursor — sibling of md-content, not inside innerHTML */
    .cursor-blink {
      display: inline-block;
      width: 7px;
      height: 1em;
      background: var(--color-accent);
      animation: cursor-blink 0.85s step-end infinite;
      vertical-align: text-bottom;
      border-radius: 1px;
      margin-left: 1px;
    }

    /* ── Markdown prose styles ─────────────────────────────────────────────── */

    .bubble.assistant :is(p, li, td, th, blockquote) {
      font-family: var(--font-sans);
      font-size: 13px;
      color: var(--color-bubble-ai-text);
    }

    .bubble.assistant p { margin: 0 0 8px; }
    .bubble.assistant p:last-child { margin-bottom: 0; }

    .bubble.assistant :is(h1, h2, h3, h4, h5, h6) {
      font-family: var(--font-sans);
      font-weight: 600;
      color: var(--color-bubble-ai-text);
      margin: 12px 0 6px;
      line-height: 1.3;
    }
    .bubble.assistant h1 { font-size: 15px; }
    .bubble.assistant h2 { font-size: 14px; }
    .bubble.assistant :is(h3, h4, h5, h6) { font-size: 13px; }

    .bubble.assistant :is(ul, ol) { padding-left: 20px; margin: 4px 0 8px; }
    .bubble.assistant li { margin: 2px 0; }

    .bubble.assistant blockquote {
      border-left: 2px solid var(--color-accent);
      margin: 8px 0;
      padding: 4px 12px;
      color: var(--color-text-secondary);
      font-style: italic;
    }

    /* Inline code */
    .bubble.assistant code {
      font-family: var(--font-mono);
      font-size: 11.5px;
      background: rgba(0, 0, 0, 0.06);
      padding: 1px 5px;
      border-radius: 3px;
      border: 1px solid var(--color-border);
    }

    [data-theme="dark"] .bubble.assistant code {
      background: rgba(255, 255, 255, 0.06);
    }

    /* Code blocks (override hljs background to match theme) */
    .bubble.assistant pre {
      background: #1A1917;
      border-radius: 6px;
      padding: 12px 14px;
      margin: 8px 0;
      overflow-x: auto;
      border: 1px solid var(--color-border-strong);
    }

    .bubble.assistant pre code {
      background: none;
      border: none;
      padding: 0;
      font-size: 12px;
      color: #E5E2D9;
      font-family: var(--font-mono);
    }

    /* Tables */
    .bubble.assistant table {
      border-collapse: collapse;
      width: 100%;
      margin: 8px 0;
      font-size: 12px;
      font-family: var(--font-mono);
      display: block;
      overflow-x: auto;
    }

    .bubble.assistant :is(th, td) {
      border: 1px solid var(--color-border-strong);
      padding: 5px 10px;
      text-align: left;
      white-space: nowrap;
    }

    .bubble.assistant th {
      background: var(--color-surface-hover);
      font-weight: 600;
      font-family: var(--font-sans);
    }

    .bubble.assistant tbody tr:nth-child(even) {
      background: var(--color-surface);
    }

    /* Images */
    .bubble.assistant img {
      max-width: 100%;
      border-radius: 6px;
      margin: 8px 0;
      display: block;
    }

    /* Horizontal rule */
    .bubble.assistant hr {
      border: none;
      border-top: 1px solid var(--color-border);
      margin: 12px 0;
    }

    /* Links */
    .bubble.assistant a {
      color: var(--color-accent);
      text-decoration: underline;
      text-underline-offset: 2px;
    }

    /* del / strikethrough */
    .bubble.assistant del { color: var(--color-text-tertiary); }

    /* ── File attachment chips ─────────────────────────────────────────────── */

    .attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .file-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 6px;
      border: 1px solid var(--color-border-strong);
      background: var(--color-surface);
      color: var(--color-text-secondary);
      font-size: 11.5px;
      font-family: var(--font-mono);
      cursor: pointer;
      transition: background var(--duration-fast) var(--ease),
                  border-color var(--duration-fast) var(--ease),
                  color var(--duration-fast) var(--ease);
    }

    .file-chip:hover {
      background: var(--color-surface-hover);
      border-color: var(--color-accent);
      color: var(--color-accent);
    }

    .file-chip svg {
      width: 13px;
      height: 13px;
      flex-shrink: 0;
    }

    .chip-size {
      font-size: 10px;
      color: var(--color-text-tertiary);
      margin-left: 2px;
    }

    /* ── Footer ────────────────────────────────────────────────────────────── */

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
          @if (message().role === 'user') {
            {{ message().content }}
          } @else {
            <!-- renderedHtml computed memoises by content string —
                 same SafeHtml reference is returned when streaming ends,
                 so Angular writes zero DOM on the done event. -->
            <div [innerHTML]="renderedHtml()"></div>
            @if (message().streaming) {
              <span class="cursor-blink" aria-hidden="true"></span>
            }
          }
        </div>

        @if (message().attachments?.length) {
          <div class="attachments">
            @for (att of message().attachments!; track att.name) {
              <button class="file-chip" (click)="downloadAttachment(att)">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6L9 1Z"/>
                  <path d="M9 1v5h5"/>
                  <line x1="6" y1="9.5" x2="10" y2="9.5"/>
                  <line x1="6" y1="12" x2="10" y2="12"/>
                </svg>
                <span>{{ att.name }}</span>
                <span class="chip-size">{{ formatSize(att.sizeBytes) }}</span>
              </button>
            }
          </div>
        }

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
  private readonly markdown = inject(MarkdownService);

  readonly message = input.required<ChatMessage>();
  readonly selectCandidate = output<string>();

  readonly renderedHtml = computed(() => this.markdown.render(this.message().content));

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
    if (m.startsWith('amazon.')) {
      const inner = m.replace('amazon.', '').replace(/-v\d+:\d+$/, '');
      return inner;
    }
    const parts = m.split('-');
    if (parts.length > 3) return parts.slice(1, 3).join('-');
    return m;
  });

  downloadAttachment(att: MessageAttachment): void {
    const blob = new Blob([att.content], { type: att.mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = att.name;
    a.click();
    URL.revokeObjectURL(url);
  }

  formatSize(bytes: number): string {
    if (bytes < 1_024) return `${bytes}B`;
    if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)}KB`;
    return `${(bytes / 1_048_576).toFixed(1)}MB`;
  }
}
