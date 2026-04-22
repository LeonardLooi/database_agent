import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { RoutingMetadata } from '../models/chat.models';

@Component({
  selector: 'app-routing-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 20px;
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 500;
      letter-spacing: 0.02em;
      white-space: nowrap;
      line-height: 1.5;
    }

    /* CHANGED: token-based colors; dark mode values live in tokens.css [Phase 6] */
    .badge.skill {
      background: var(--color-teal-muted);
      color: var(--color-teal);
      border: 1px solid var(--color-teal-border);
    }

    .badge.clarify {
      background: rgba(245, 158, 11, 0.10);
      color: #92400e;
      border: 1px solid rgba(245, 158, 11, 0.28);
    }

    .badge.generic {
      background: color-mix(in srgb, var(--color-text-tertiary) 10%, transparent);
      color: var(--color-text-tertiary);
      border: 1px solid color-mix(in srgb, var(--color-border-strong) 50%, transparent);
    }

    :host-context([data-theme="dark"]) .badge.clarify {
      color: #fbbf24;
      background: rgba(251, 191, 36, 0.10);
      border-color: rgba(251, 191, 36, 0.28);
    }
  `],
  template: `
    @if (meta()) {
      <span class="badge" [class]="badgeClass()">{{ label() }}</span>
    }
  `,
})
export class RoutingBadgeComponent {
  readonly meta = input<RoutingMetadata | undefined>(undefined);

  readonly badgeClass = computed(() => {
    switch (this.meta()?.routing_decision) {
      case 'CALL_SKILL':     return 'badge skill';
      case 'CLARIFY':        return 'badge clarify';
      default:               return 'badge generic';
    }
  });

  readonly label = computed(() => {
    switch (this.meta()?.routing_decision) {
      case 'CALL_SKILL':     return '⚙ Tool Used';
      case 'CLARIFY':        return '? Clarifying';
      default:               return '✦ General Answer';
    }
  });
}
