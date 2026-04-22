import {
  Injectable,
  computed,
  inject,
  signal,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { v4 as uuidv4 } from 'uuid';
import {
  ChatMessage,
  Conversation,
  WsClarificationRequest,
  WsDelta,
  WsDone,
  WsTitle,
} from '../../shared/models/chat.models';
import { ChatWsService } from './chat-ws.service';
import { ProvidersService } from './providers.service';
import { AuthService } from './auth.service';

interface ApiConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ApiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provider: string;
  model: string;
  token_count: number;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ConversationService {
  private readonly ws = inject(ChatWsService);
  private readonly providers = inject(ProvidersService);
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private readonly _conversations = signal<Conversation[]>([]);
  private readonly _activeId = signal<string | null>(null);
  private readonly _streaming = signal(false);
  private readonly _loadedIds = new Set<string>();

  readonly conversations = this._conversations.asReadonly();
  readonly activeId = this._activeId.asReadonly();
  readonly streaming = this._streaming.asReadonly();

  readonly activeConversation = computed(() =>
    this._conversations().find((c) => c.id === this._activeId()),
  );

  readonly activeMessages = computed(
    () => this.activeConversation()?.messages ?? [],
  );

  constructor() {
    this.ws.messages$.subscribe((msg) => {
      switch (msg.type) {
        case 'delta':                this.onDelta(msg);                         break;
        case 'done':                 this.onDone(msg);                          break;
        case 'title':                this.onTitle(msg);                         break;
        case 'error':                this.onError();                            break;
        case 'clarification_request': this.onClarification(msg);               break;
      }
    });
  }

  async loadHistory(): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    try {
      const convs = await firstValueFrom(
        this.http.get<ApiConversation[]>(`/api/conversations?token=${token}`)
      );
      if (!convs?.length) return;
      const mapped: Conversation[] = convs.map((c) => ({
        id: c.id,
        title: c.title,
        messages: [],
        createdAt: new Date(c.created_at),
        updatedAt: new Date(c.updated_at),
      }));
      this._conversations.set(mapped);
      this._activeId.set(mapped[0].id);
      await this.loadMessages(mapped[0].id);
    } catch {
      // Backend unreachable — start fresh
    }
  }

  async loadMessages(id: string): Promise<void> {
    if (this._loadedIds.has(id)) return;
    const token = this.auth.token();
    if (!token) return;
    try {
      const msgs = await firstValueFrom(
        this.http.get<ApiMessage[]>(`/api/conversations/${id}/messages?token=${token}`)
      );
      this._loadedIds.add(id);
      this.patchConversation(id, (c) => ({
        ...c,
        messages: msgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          provider: m.provider,
          model: m.model,
          tokenCount: m.token_count,
        })),
      }));
    } catch {
      this._loadedIds.add(id); // don't retry on error
    }
  }

  newConversation(): void {
    const conv: Conversation = {
      id: uuidv4(),
      title: 'New Chat',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this._conversations.update((cs) => [conv, ...cs]);
    this._activeId.set(conv.id);
    this._loadedIds.add(conv.id); // nothing to load from server
  }

  async selectConversation(id: string): Promise<void> {
    this._activeId.set(id);
    await this.loadMessages(id);
  }

  deleteConversation(id: string): void {
    const token = this.auth.token();
    if (token) {
      this.http.delete(`/api/conversations/${id}?token=${token}`).subscribe();
    }
    this._loadedIds.delete(id);
    this._conversations.update((cs) => cs.filter((c) => c.id !== id));
    if (this._activeId() === id) {
      const remaining = this._conversations();
      this._activeId.set(remaining[0]?.id ?? null);
    }
  }

  sendMessage(content: string): void {
    const conv = this.activeConversation();
    if (!conv || this._streaming()) return;

    const userMsg: ChatMessage = { id: uuidv4(), role: 'user', content };
    const placeholderMsg: ChatMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      streaming: true,
    };

    this.patchConversation(conv.id, (c) => ({
      ...c,
      messages: [...c.messages, userMsg, placeholderMsg],
      updatedAt: new Date(),
    }));

    this._streaming.set(true);

    const history = conv.messages.map((m) => ({ role: m.role, content: m.content }));
    history.push({ role: 'user', content });

    this.ws.send({
      type: 'message',
      conversation_id: conv.id,
      messages: history,
      model: this.providers.selectedModel(),
      temperature: 0.7,
    });
  }

  private onDelta(msg: WsDelta): void {
    const convId = this._activeId();
    if (!convId) return;
    this.patchConversation(convId, (c) => {
      const messages = [...c.messages];
      const lastIdx = messages.length - 1;
      if (messages[lastIdx]?.streaming) {
        messages[lastIdx] = {
          ...messages[lastIdx],
          content: messages[lastIdx].content + msg.content,
        };
      }
      return { ...c, messages };
    });
  }

  private onDone(msg: WsDone): void {
    this._streaming.set(false);
    const convId = msg.conversation_id || this._activeId();
    if (!convId) return;
    this.patchConversation(convId, (c) => {
      const messages = [...c.messages];
      const lastIdx = messages.length - 1;
      if (messages[lastIdx]?.streaming) {
        messages[lastIdx] = {
          ...messages[lastIdx],
          streaming: false,
          provider: msg.provider,
          model: msg.model,
          tokenCount: msg.token_count,
          routingMetadata: msg.routing_metadata,
        };
      }
      return { ...c, messages, updatedAt: new Date() };
    });
  }

  private onTitle(msg: WsTitle): void {
    this.patchConversation(msg.conversation_id, (c) => ({
      ...c,
      title: msg.title,
    }));
  }

  private onError(): void {
    this._streaming.set(false);
    const convId = this._activeId();
    if (!convId) return;
    this.patchConversation(convId, (c) => ({
      ...c,
      messages: c.messages.map((m) =>
        m.streaming ? { ...m, streaming: false, error: true, content: '⚠ Response failed.' } : m,
      ),
    }));
  }

  private onClarification(msg: WsClarificationRequest): void {
    this._streaming.set(false);
    const convId = this._activeId();
    if (!convId) return;
    const clarMsg: ChatMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: msg.message,
      clarification: { message: msg.message, candidates: msg.candidates, answered: false },
    };
    this.patchConversation(convId, (c) => ({
      ...c,
      messages: [...c.messages, clarMsg],
    }));
  }

  selectClarification(messageId: string, candidate: string): void {
    const convId = this._activeId();
    if (!convId || this._streaming()) return;
    this.patchConversation(convId, (c) => ({
      ...c,
      messages: c.messages.map((m) =>
        m.id === messageId && m.clarification
          ? { ...m, clarification: { ...m.clarification, answered: true } }
          : m,
      ),
    }));
    this.sendMessage(candidate);
  }

  private patchConversation(
    id: string,
    updater: (c: Conversation) => Conversation,
  ): void {
    this._conversations.update((cs) =>
      cs.map((c) => (c.id === id ? updater(c) : c)),
    );
  }
}
