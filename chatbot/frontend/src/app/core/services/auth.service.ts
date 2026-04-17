import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap, catchError, of, firstValueFrom } from 'rxjs';

interface GuestTokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
}

const TOKEN_KEY = 'chatbot_auth_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  readonly token = signal<string | null>(null);
  readonly userId = signal<string | null>(null);

  async init(): Promise<void> {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      this.token.set(stored);
      return;
    }
    await this.requestGuestToken();
  }

  private async requestGuestToken(): Promise<void> {
    try {
      const res = await firstValueFrom(
        this.http.post<GuestTokenResponse>('/auth/guest', {}).pipe(
          tap((r) => {
            this.token.set(r.access_token);
            this.userId.set(r.user_id);
            localStorage.setItem(TOKEN_KEY, r.access_token);
          }),
          catchError(() => of(null)),
        ),
      );
      if (!res) {
        const fallback = `guest_${Math.random().toString(36).slice(2, 10)}`;
        this.userId.set(fallback);
      }
    } catch {
      // Offline — WS will fail gracefully
    }
  }

  clearToken(): void {
    this.token.set(null);
    this.userId.set(null);
    localStorage.removeItem(TOKEN_KEY);
  }
}
