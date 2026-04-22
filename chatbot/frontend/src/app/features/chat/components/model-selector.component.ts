import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import { ProvidersService } from '../../../core/services/providers.service';
import { AuthService } from '../../../core/services/auth.service';
import { ConversationService } from '../../../core/services/conversation.service';

@Component({
  selector: 'app-model-selector',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .segment-group {
      display: flex;
      align-items: center;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 8px;
      padding: 2px;
      gap: 1px;
    }

    .provider-sep {
      width: 1px;
      height: 16px;
      background: var(--color-border);
      margin: 0 1px;
      flex-shrink: 0;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 500;
      letter-spacing: 0.01em;
      cursor: pointer;
      border: none;
      background: transparent;
      color: var(--color-text-secondary);
      white-space: nowrap;
      transition: background var(--duration-fast) var(--ease), color var(--duration-fast) var(--ease);
      line-height: 1.4;
    }

    .pill:hover:not(.active):not(:disabled) {
      background: var(--color-surface-hover);
      color: var(--color-text-primary);
    }

    .pill.active {
      background: var(--color-accent);
      color: #fff;
      cursor: default;
    }

    .pill:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .toast {
      position: fixed;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--color-surface-active);
      border: 1px solid var(--color-border);
      color: var(--color-text-primary);
      font-size: 12px;
      font-family: var(--font-mono);
      padding: 7px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
      pointer-events: none;
      z-index: 9999;
      white-space: nowrap;
      animation: fadeInUp 0.15s ease;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateX(-50%) translateY(6px); }
      to   { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
  `],
  template: `
    @if (providers.hasProviders()) {
      <div class="segment-group" role="group" aria-label="Select AI model" (keydown)="onGroupKeydown($event)">
        @for (group of providers.providerGroups(); track group.provider; let last = $last) {
          @for (model of group.models; track model) {
            <button
              class="pill"
              [class.active]="providers.selectedModel() === model"
              [disabled]="providers.switching()"
              (click)="onSelect(model)"
              [title]="group.label + ': ' + model"
              [attr.aria-pressed]="providers.selectedModel() === model"
            >{{ shortLabel(model) }}</button>
          }
          @if (!last) {
            <div class="provider-sep" aria-hidden="true"></div>
          }
        }
      </div>
    }

    @if (providers.toast()) {
      <div class="toast" role="status" aria-live="polite">{{ providers.toast() }}</div>
    }
  `,
})
export class ModelSelectorComponent {
  protected readonly providers = inject(ProvidersService);
  private readonly auth = inject(AuthService);
  private readonly conversations = inject(ConversationService);

  /** Arrow-key navigation within the segment group. */
  protected onGroupKeydown(event: KeyboardEvent): void {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    const pills = (event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('button.pill:not(:disabled)');
    const arr = Array.from(pills);
    const idx = arr.indexOf(document.activeElement as HTMLButtonElement);
    if (idx === -1) return;
    event.preventDefault();
    const next = event.key === 'ArrowRight' ? (idx + 1) % arr.length : (idx - 1 + arr.length) % arr.length;
    arr[next].focus();
  }

  protected async onSelect(model: string): Promise<void> {
    if (model === this.providers.selectedModel() || this.providers.switching()) return;
    const convId = this.conversations.activeId();
    const token = this.auth.token();
    if (!convId || !token) {
      this.providers.selectModel(model);
      return;
    }
    await this.providers.switchModel(convId, model, token);
  }

  protected shortLabel(model: string): string {
    // Abbreviate long model IDs for the pill label
    const map: Record<string, string> = {
      'claude-opus-4-20250514':    'Opus 4',
      'claude-sonnet-4-20250514':  'Sonnet 4',
      'claude-haiku-4-20251001':   'Haiku 4.5',
      'gpt-4o':                    'GPT-4o',
      'gpt-4o-mini':               '4o-mini',
      'o1':                        'o1',
      'o3-mini':                   'o3-mini',
      'gemini-2.5-pro':            '2.5 Pro',
      'gemini-2.0-flash':          '2.0 Flash',
      'gemini-2.0-flash-lite':     'Flash Lite',
      'amazon.nova-pro-v1:0':      'Nova Pro',
      'amazon.nova-lite-v1:0':     'Nova Lite',
      'amazon.nova-micro-v1:0':    'Nova Micro',
    };
    return map[model] ?? model;
  }
}
