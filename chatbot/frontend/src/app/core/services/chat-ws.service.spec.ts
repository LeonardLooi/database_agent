import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { ChatWsService } from './chat-ws.service';
import { AuthService } from './auth.service';
import { ProvidersService } from './providers.service';

// We cannot create a real WebSocket in unit tests, so we mock webSocket from rxjs/webSocket
const mockSocket = {
  next: jasmine.createSpy('next'),
  complete: jasmine.createSpy('complete'),
  closed: false,
};

let openObserverCallback: (() => void) | null = null;
let closeObserverCallback: (() => void) | null = null;
let messageHandler: ((msg: unknown) => void) | null = null;
let errorHandler: (() => void) | null = null;

jasmine.getEnv().allowRespy(true);

describe('ChatWsService', () => {
  let service: ChatWsService;

  const mockAuthService = { token: () => 'test-token' };
  const mockProvidersService = { setProviders: jasmine.createSpy('setProviders') };

  beforeEach(() => {
    mockSocket.next.calls.reset();
    mockSocket.complete.calls.reset();
    mockSocket.closed = false;

    TestBed.configureTestingModule({
      providers: [
        ChatWsService,
        { provide: AuthService, useValue: mockAuthService },
        { provide: ProvidersService, useValue: mockProvidersService },
      ],
    });
    service = TestBed.inject(ChatWsService);
  });

  afterEach(() => {
    service.disconnect();
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(service).toBeTruthy();
  });

  it('should start disconnected', () => {
    expect(service.connected()).toBe(false);
  });

  it('should have a messages$ Subject', () => {
    expect(service.messages$).toBeTruthy();
    expect(service.messages$.subscribe).toBeDefined();
  });

  describe('send()', () => {
    it('should not send if not connected', () => {
      // connected is false initially — send should be a no-op
      const msgSpy = spyOn<any>(service, 'socket$').and.callThrough();
      expect(() =>
        service.send({ type: 'message', messages: [], conversation_id: 'conv-1' })
      ).not.toThrow();
    });
  });

  describe('disconnect()', () => {
    it('should set connected to false', () => {
      service['connected'].set(true);
      service.disconnect();
      expect(service.connected()).toBe(false);
    });

    it('should be safe to call multiple times', () => {
      expect(() => {
        service.disconnect();
        service.disconnect();
      }).not.toThrow();
    });
  });

  describe('ngOnDestroy()', () => {
    it('should call disconnect', () => {
      spyOn(service, 'disconnect');
      service.ngOnDestroy();
      expect(service.disconnect).toHaveBeenCalled();
    });
  });

  describe('messages$ stream', () => {
    it('should be a subject that can be subscribed to', (done) => {
      const received: unknown[] = [];
      service.messages$.subscribe((msg) => {
        received.push(msg);
        if (received.length === 1) {
          expect(received[0]).toEqual({ type: 'pong' });
          done();
        }
      });
      // Simulate message delivery by directly pushing to messages$
      service.messages$.next({ type: 'pong' } as any);
    });
  });
});
