import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
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
  aws: 'AWS Bedrock',
};

const MODEL_STORAGE_KEY = 'preferred_model';

@Injectable({ providedIn: 'root' })
export class ProvidersService {
  private readonly http = inject(HttpClient);

  private readonly _providers = signal<WsProviderInfo[]>([]);
  private readonly _selectedModel = signal<string>('');
  private readonly _switching = signal(false);
  private readonly _toast = signal<string>('');

  readonly providers = this._providers.asReadonly();
  readonly selectedModel = this._selectedModel.asReadonly();
  readonly switching = this._switching.asReadonly();
  readonly toast = this._toast.asReadonly();

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
    if (!this._selectedModel()) {
      const stored = localStorage.getItem(MODEL_STORAGE_KEY);
      const allModels = data.flatMap((p) => p.models);
      if (stored && allModels.includes(stored)) {
        this._selectedModel.set(stored);
      } else if (data.length > 0) {
        const first = data[0];
        this._selectedModel.set(first.default_model || first.models[0] || '');
      }
    }
  }

  selectModel(model: string): void {
    this._selectedModel.set(model);
    localStorage.setItem(MODEL_STORAGE_KEY, model);
  }

  async switchModel(conversationId: string, model: string, token: string): Promise<void> {
    const previous = this._selectedModel();
    this._selectedModel.set(model); // optimistic update
    this._switching.set(true);

    try {
      await firstValueFrom(
        this.http.patch(
          `/api/sessions/${conversationId}/model?token=${token}`,
          { model },
        ),
      );
      localStorage.setItem(MODEL_STORAGE_KEY, model);
      this._showToast(`Switched to ${model}`);
    } catch {
      this._selectedModel.set(previous); // revert on error
      this._showToast('Model switch failed — reverted');
    } finally {
      this._switching.set(false);
    }
  }

  providerForModel(model: string): string {
    for (const p of this._providers()) {
      if (p.models.includes(model)) return p.provider;
    }
    return '';
  }

  private _showToast(message: string): void {
    this._toast.set(message);
    setTimeout(() => this._toast.set(''), 3000);
  }
}
