import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { ChatInputComponent } from './chat-input.component';
import { ConversationService } from '../../core/services/conversation.service';
import { ChatWsService } from '../../core/services/chat-ws.service';
import { signal } from '@angular/core';

describe('ChatInputComponent', () => {
  let fixture: ComponentFixture<ChatInputComponent>;
  let component: ChatInputComponent;

  const mockConvService = {
    streaming: signal(false),
    activeConversation: signal({ id: 'conv-1', title: 'Test', messages: [], createdAt: new Date(), updatedAt: new Date() }),
    newConversation: jasmine.createSpy('newConversation'),
    sendMessage: jasmine.createSpy('sendMessage'),
  };

  const mockWsService = {
    connected: signal(true),
    connect: jasmine.createSpy('connect'),
    send: jasmine.createSpy('send'),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatInputComponent, FormsModule],
      providers: [
        { provide: ConversationService, useValue: mockConvService },
        { provide: ChatWsService, useValue: mockWsService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    mockConvService.sendMessage.calls.reset();
    mockConvService.newConversation.calls.reset();
    mockWsService.connect.calls.reset();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call ws.connect on init', () => {
    expect(mockWsService.connect).toHaveBeenCalled();
  });

  it('should render textarea', () => {
    const textarea = fixture.nativeElement.querySelector('textarea');
    expect(textarea).toBeTruthy();
  });

  it('should render send button', () => {
    const btn = fixture.nativeElement.querySelector('button');
    expect(btn).toBeTruthy();
  });

  it('should disable input when streaming', () => {
    mockConvService.streaming.set(true);
    fixture.detectChanges();
    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    expect(textarea.disabled).toBe(true);
    mockConvService.streaming.set(false);
  });

  it('should disable input when disconnected', () => {
    mockWsService.connected.set(false);
    fixture.detectChanges();
    const textarea: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    expect(textarea.disabled).toBe(true);
    mockWsService.connected.set(true);
  });

  it('should call sendMessage on submit with draft text', () => {
    component['draft'] = 'Hello world';
    component['submit']();
    expect(mockConvService.sendMessage).toHaveBeenCalledWith('Hello world');
    expect(component['draft']).toBe('');
  });

  it('should not send empty or whitespace-only messages', () => {
    component['draft'] = '   ';
    component['submit']();
    expect(mockConvService.sendMessage).not.toHaveBeenCalled();
  });

  it('should send on Enter key (no shift)', () => {
    component['draft'] = 'test message';
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
    const preventDefaultSpy = spyOn(event, 'preventDefault');
    component['onKeyDown'](event);
    expect(preventDefaultSpy).toHaveBeenCalled();
    expect(mockConvService.sendMessage).toHaveBeenCalledWith('test message');
  });

  it('should not send on Shift+Enter', () => {
    component['draft'] = 'test message';
    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true });
    const preventDefaultSpy = spyOn(event, 'preventDefault');
    component['onKeyDown'](event);
    expect(preventDefaultSpy).not.toHaveBeenCalled();
    expect(mockConvService.sendMessage).not.toHaveBeenCalled();
  });

  it('should show connected status dot', () => {
    mockWsService.connected.set(true);
    fixture.detectChanges();
    const dot = fixture.nativeElement.querySelector('.status-dot');
    expect(dot.classList.contains('connected')).toBe(true);
  });

  it('should show disconnected status when not connected', () => {
    mockWsService.connected.set(false);
    fixture.detectChanges();
    const dot = fixture.nativeElement.querySelector('.status-dot');
    expect(dot.classList.contains('disconnected')).toBe(true);
    mockWsService.connected.set(true);
  });
});
