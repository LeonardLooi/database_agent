import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { Subject } from 'rxjs';
import { ConversationService } from './conversation.service';
import { ChatWsService } from './chat-ws.service';
import { ProvidersService } from './providers.service';
import { AuthService } from './auth.service';
import { WsIncoming } from '../../shared/models/chat.models';

describe('ConversationService', () => {
  let service: ConversationService;
  let httpMock: HttpTestingController;
  let wsMessages$: Subject<WsIncoming>;

  const mockWsService = {
    messages$: new Subject<WsIncoming>(),
    send: jasmine.createSpy('send'),
  };

  const mockProvidersService = {
    selectedModel: () => 'claude-3-sonnet',
  };

  const mockAuthService = {
    token: () => 'test-token',
    userId: () => 'user_test',
  };

  beforeEach(() => {
    wsMessages$ = new Subject<WsIncoming>();
    mockWsService.messages$ = wsMessages$ as any;

    TestBed.configureTestingModule({
      providers: [
        ConversationService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ChatWsService, useValue: mockWsService },
        { provide: ProvidersService, useValue: mockProvidersService },
        { provide: AuthService, useValue: mockAuthService },
      ],
    });
    service = TestBed.inject(ConversationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create', () => {
    expect(service).toBeTruthy();
  });

  it('should start with empty conversations and null activeId', () => {
    expect(service.conversations()).toEqual([]);
    expect(service.activeId()).toBeNull();
    expect(service.streaming()).toBe(false);
  });

  describe('newConversation()', () => {
    it('should add a new conversation and set it as active', () => {
      service.newConversation();
      expect(service.conversations().length).toBe(1);
      expect(service.activeId()).toBeTruthy();
      expect(service.conversations()[0].title).toBe('New Chat');
    });

    it('should prepend new conversation to the list', () => {
      service.newConversation();
      const firstId = service.activeId();
      service.newConversation();
      expect(service.conversations()[0].id).not.toBe(firstId);
      expect(service.conversations().length).toBe(2);
    });
  });

  describe('loadHistory()', () => {
    it('should load conversations from API and set first as active', async () => {
      const promise = service.loadHistory();
      const req = httpMock.expectOne('/api/conversations?token=test-token');
      req.flush([
        { id: 'conv-1', title: 'First', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
        { id: 'conv-2', title: 'Second', created_at: '2024-01-02T00:00:00Z', updated_at: '2024-01-02T00:00:00Z' },
      ]);
      // loadMessages is called for first conversation
      const msgsReq = httpMock.expectOne('/api/conversations/conv-1/messages?token=test-token');
      msgsReq.flush([]);
      await promise;

      expect(service.conversations().length).toBe(2);
      expect(service.activeId()).toBe('conv-1');
    });

    it('should do nothing on empty history', async () => {
      const promise = service.loadHistory();
      const req = httpMock.expectOne('/api/conversations?token=test-token');
      req.flush([]);
      await promise;
      expect(service.conversations()).toEqual([]);
    });

    it('should handle API error gracefully', async () => {
      const promise = service.loadHistory();
      const req = httpMock.expectOne('/api/conversations?token=test-token');
      req.error(new ErrorEvent('network error'));
      await promise;
      expect(service.conversations()).toEqual([]);
    });
  });

  describe('deleteConversation()', () => {
    it('should remove conversation and update active id', () => {
      service.newConversation();
      const id = service.activeId()!;
      service.deleteConversation(id);

      expect(service.conversations().find((c) => c.id === id)).toBeUndefined();
      httpMock.expectOne(`/api/conversations/${id}?token=test-token`);
    });

    it('should switch active to next conversation after deletion', () => {
      service.newConversation();
      service.newConversation();
      const activeId = service.activeId()!;

      service.deleteConversation(activeId);
      httpMock.expectOne(`/api/conversations/${activeId}?token=test-token`);

      expect(service.conversations().length).toBe(1);
      expect(service.activeId()).not.toBe(activeId);
    });
  });

  describe('sendMessage()', () => {
    it('should add user and placeholder messages and call ws.send', () => {
      service.newConversation();
      service.sendMessage('Hello');

      const messages = service.activeMessages();
      expect(messages.length).toBe(2);
      expect(messages[0].role).toBe('user');
      expect(messages[0].content).toBe('Hello');
      expect(messages[1].role).toBe('assistant');
      expect(messages[1].streaming).toBe(true);
      expect(mockWsService.send).toHaveBeenCalled();
    });

    it('should set streaming to true when sending', () => {
      service.newConversation();
      service.sendMessage('Test');
      expect(service.streaming()).toBe(true);
    });

    it('should not send if no active conversation', () => {
      mockWsService.send.calls.reset();
      service.sendMessage('no conv');
      expect(mockWsService.send).not.toHaveBeenCalled();
    });

    it('should not send if already streaming', () => {
      service.newConversation();
      service.sendMessage('First');
      mockWsService.send.calls.reset();
      service.sendMessage('Second while streaming');
      expect(mockWsService.send).not.toHaveBeenCalled();
    });
  });

  describe('WebSocket message handling', () => {
    beforeEach(() => {
      service.newConversation();
      service.sendMessage('test');
    });

    it('should append delta content to streaming message', () => {
      wsMessages$.next({ type: 'delta', content: 'Hello' });
      wsMessages$.next({ type: 'delta', content: ' world' });
      const msgs = service.activeMessages();
      expect(msgs[msgs.length - 1].content).toBe('Hello world');
    });

    it('should finalize message on done frame', () => {
      wsMessages$.next({ type: 'delta', content: 'response' });
      wsMessages$.next({
        type: 'done',
        conversation_id: service.activeId()!,
        token_count: 5,
        provider: 'anthropic',
        model: 'claude-3-sonnet',
      });
      const msgs = service.activeMessages();
      const last = msgs[msgs.length - 1];
      expect(last.streaming).toBe(false);
      expect(last.provider).toBe('anthropic');
      expect(last.tokenCount).toBe(5);
      expect(service.streaming()).toBe(false);
    });

    it('should update conversation title on title frame', () => {
      const convId = service.activeId()!;
      wsMessages$.next({ type: 'title', conversation_id: convId, title: 'My Chat' });
      const conv = service.conversations().find((c) => c.id === convId);
      expect(conv?.title).toBe('My Chat');
    });

    it('should mark message as error on error frame', () => {
      wsMessages$.next({ type: 'error', message: 'LLM error', code: 500 });
      const msgs = service.activeMessages();
      const last = msgs[msgs.length - 1];
      expect(last.error).toBe(true);
      expect(last.streaming).toBe(false);
      expect(service.streaming()).toBe(false);
    });

    it('should add clarification message on clarification_request', () => {
      service['_streaming'].set(false); // reset so we can track
      const before = service.activeMessages().length;
      wsMessages$.next({
        type: 'clarification_request',
        message: 'Which table?',
        candidates: ['orders', 'customers'],
      });
      const msgs = service.activeMessages();
      expect(msgs.length).toBe(before + 1);
      const clarMsg = msgs[msgs.length - 1];
      expect(clarMsg.clarification?.message).toBe('Which table?');
      expect(clarMsg.clarification?.candidates).toEqual(['orders', 'customers']);
    });
  });
});
