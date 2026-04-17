import { Injectable, computed, signal } from '@angular/core';
import { WsProviderInfo } from '../../shared/models/chat.models';

export interface ProviderGroup {
  provider: string;
  label: string;
  models: string[];
  defaultModel: string;
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  gemini: 'Google Gemini',
};

@Injectable({ providedIn: 'root' })
export class ProvidersService {
  private readonly _providers = signal<WsProviderInfo[]>([]);
  private readonly _selectedModel = signal<string>('');

  readonly providers = this._providers.asReadonly();
  readonly selectedModel = this._selectedModel.asReadonly();

  readonly providerGroups = computed<ProviderGroup[]>(() =>
    this._providers().map((p) => ({
      provider: p.provider,
      label: PROVIDER_LABELS[p.provider] ?? p.provider,
      models: p.models,
      defaultModel: p.default_model,
    })),
  );

  readonly hasProviders = computed(() => this._providers().length > 0);

  setProviders(data: WsProviderInfo[]): void {
    this._providers.set(data);
    if (!this._selectedModel() && data.length > 0) {
      const first = data[0];
      this._selectedModel.set(first.default_model || first.models[0] || '');
    }
  }

  selectModel(model: string): void {
    this._selectedModel.set(model);
  }

  providerForModel(model: string): string {
    for (const p of this._providers()) {
      if (p.models.includes(model)) return p.provider;
    }
    return '';
  }
}
