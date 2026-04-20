import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  inject,
} from '@angular/core';
import { ScrollingModule } from '@angular/cdk/scrolling';
import { ConversationService } from '../../core/services/conversation.service';
import { MessageBubbleComponent } from '../../shared/components/message-bubble.component';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [ScrollingModule, MessageBubbleComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      flex: 1 1 0%;
      min-height: 0;
      overflow: hidden;
    }

    .scroll-area {
      flex: 1;
      overflow-y: auto;
      padding: 32px 0 20px;
    }

    /* ── Empty state with data-grid aesthetic ── */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      text-align: center;
      padding: 0 40px;
      gap: 0;
      position: relative;
    }

    /* Subtle dot grid background */
    .empty-state::before {
      content: '';
      position: absolute;
      inset: 0;
      background-image: radial-gradient(
        circle,
        var(--color-border) 1px,
        transparent 1px
      );
      background-size: 28px 28px;
      opacity: 0.5;
      pointer-events: none;
    }

    .empty-inner {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
    }

    .empty-icon-wrap {
      width: 52px;
      height: 52px;
      border-radius: 12px;
      background: var(--color-surface);
      border: 1px solid var(--color-border-strong);
      box-shadow: 0 0 0 4px var(--color-accent-subtle),
                  0 0 24px var(--color-accent-subtle);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .empty-icon-wrap svg {
      width: 22px;
      height: 22px;
      stroke: var(--color-accent);
      stroke-width: 1.5;
    }

    .empty-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--color-text-primary);
      letter-spacing: -0.015em;
      margin: 0;
      font-family: var(--font-sans);
    }

    .empty-desc {
      font-size: 12px;
      color: var(--color-text-tertiary);
      margin: 0;
      line-height: 1.6;
      font-family: var(--font-mono);
      letter-spacing: 0.01em;
    }

    .empty-chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: center;
      margin-top: 4px;
    }

    .chip {
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid var(--color-border-strong);
      background: var(--color-surface);
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--color-text-secondary);
      letter-spacing: 0.02em;
    }
  `],
  template: `
    <div #scrollContainer class="scroll-area">
      @if (conversations.activeMessages().length === 0) {
        <div class="empty-state">
          <div class="empty-inner">
            <div class="empty-icon-wrap">
              <svg fill="none" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 5v4c0 1.66-4.03 3-9 3S3 10.66 3 9V5"/>
                <path d="M21 9v4c0 1.66-4.03 3-9 3S3 14.66 3 13V9"/>
                <path d="M21 13v4c0 1.66-4.03 3-9 3s-9-1.34-9-3v-4"/>
              </svg>
            </div>
            <p class="empty-title">Ask your database anything</p>
            <p class="empty-desc">SQL · analysis · schemas · insights</p>
            <div class="empty-chips">
              <span class="chip">SELECT *</span>
              <span class="chip">GROUP BY</span>
              <span class="chip">EXPLAIN</span>
            </div>
          </div>
        </div>
      } @else {
        @for (msg of conversations.activeMessages(); track msg.id) {
          <app-message-bubble
            [message]="msg"
            (selectCandidate)="conversations.selectClarification(msg.id, $event)"
          />
        }
        <div #anchor></div>
      }
    </div>
  `,
})
export class ChatWindowComponent implements AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('anchor') private anchor!: ElementRef<HTMLDivElement>;

  readonly conversations = inject(ConversationService);

  private lastMessageCount = 0;

  ngAfterViewChecked(): void {
    const count = this.conversations.activeMessages().length;
    if (count !== this.lastMessageCount || this.conversations.streaming()) {
      this.lastMessageCount = count;
      this.scrollToBottom();
    }
  }

  private scrollToBottom(): void {
    try {
      this.anchor?.nativeElement?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    } catch {
      // scrollIntoView not available in test env
    }
  }
}
