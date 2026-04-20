import {
  Injectable,
  OnDestroy,
  inject,
  signal,
} from '@angular/core';
import { Subject, Subscription, timer } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { WsIncoming, WsOutgoing } from '../../shared/models/chat.models';
import { AuthService } from './auth.service';
import { ProvidersService } from './providers.service';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatWsService implements OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly providers = inject(ProvidersService);

  private socket$: WebSocketSubject<WsIncoming | WsOutgoing> | null = null;
  private heartbeat$: Subscription | null = null;
  private reconnect$: Subscription | null = null;
  private msgSubscription$: Subscription | null = null;

  readonly connected = signal(false);
  readonly messages$ = new Subject<WsIncoming>();

  connect(): void {
    const token = this.auth.token();
    if (!token) return;
    if (this.socket$ && !this.socket$.closed) return;

    const wsBase = environment.wsUrl || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;
    const url = `${wsBase}/ws/chat?token=${token}`;

    this.socket$ = webSocket<WsIncoming | WsOutgoing>({
      url,
      openObserver: {
        next: () => {
          this.connected.set(true);
          this.startHeartbeat();
        },
      },
      closeObserver: {
        next: () => {
          this.connected.set(false);
          this.stopHeartbeat();
          this.scheduleReconnect();
        },
      },
    });

    this.msgSubscription$ = this.socket$.subscribe({
      next: (msg) => this.handleMessage(msg as WsIncoming),
      error: () => {
        this.connected.set(false);
        this.stopHeartbeat();
        this.scheduleReconnect();
      },
    });
  }

  send(msg: WsOutgoing): void {
    if (this.connected()) {
      this.socket$?.next(msg);
    }
  }

  disconnect(): void {
    this.reconnect$?.unsubscribe();
    this.stopHeartbeat();
    this.msgSubscription$?.unsubscribe();
    this.socket$?.complete();
    this.socket$ = null;
    this.connected.set(false);
  }

  private handleMessage(msg: WsIncoming): void {
    if (msg.type === 'providers') {
      this.providers.setProviders(msg.data);
    }
    this.messages$.next(msg);
  }

  private startHeartbeat(): void {
    const interval = 25_000;
    this.heartbeat$ = timer(interval, interval).subscribe(() =>
      this.send({ type: 'ping' }),
    );
  }

  private stopHeartbeat(): void {
    this.heartbeat$?.unsubscribe();
    this.heartbeat$ = null;
  }

  private scheduleReconnect(): void {
    this.reconnect$?.unsubscribe();
    this.reconnect$ = timer(3_000).subscribe(() => this.connect());
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
