import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { ProvidersService } from './providers.service';
import { WsProviderInfo } from '../../shared/models/chat.models';

const mockProviders: WsProviderInfo[] = [
  { provider: 'anthropic', models: ['claude-3-opus', 'claude-3-sonnet'], default_model: 'claude-3-sonnet' },
  { provider: 'openai', models: ['gpt-4o', 'gpt-4'], default_model: 'gpt-4o' },
];

describe('ProvidersService', () => {
  let service: ProvidersService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [ProvidersService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ProvidersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should create', () => {
    expect(service).toBeTruthy();
  });

  it('should have empty providers initially', () => {
    expect(service.providers()).toEqual([]);
    expect(service.hasProviders()).toBe(false);
  });

  describe('setProviders()', () => {
    it('should set providers and select default model', () => {
      service.setProviders(mockProviders);
      expect(service.providers()).toEqual(mockProviders);
      expect(service.selectedModel()).toBe('claude-3-sonnet');
      expect(service.hasProviders()).toBe(true);
    });

    it('should use stored model if present and valid', () => {
      localStorage.setItem('preferred_model', 'gpt-4o');
      service.setProviders(mockProviders);
      expect(service.selectedModel()).toBe('gpt-4o');
    });

    it('should ignore stored model if not in available models', () => {
      localStorage.setItem('preferred_model', 'invalid-model');
      service.setProviders(mockProviders);
      expect(service.selectedModel()).toBe('claude-3-sonnet');
    });

    it('should not change model if already selected', () => {
      service.selectModel('gpt-4');
      service.setProviders(mockProviders);
      expect(service.selectedModel()).toBe('gpt-4');
    });
  });

  describe('selectModel()', () => {
    it('should update selectedModel and persist to localStorage', () => {
      service.setProviders(mockProviders);
      service.selectModel('gpt-4o');
      expect(service.selectedModel()).toBe('gpt-4o');
      expect(localStorage.getItem('preferred_model')).toBe('gpt-4o');
    });
  });

  describe('providerGroups computed', () => {
    it('should map providers to groups with labels', () => {
      service.setProviders(mockProviders);
      const groups = service.providerGroups();
      expect(groups.length).toBe(2);
      expect(groups[0].label).toBe('Anthropic');
      expect(groups[1].label).toBe('OpenAI');
    });
  });

  describe('providerForModel()', () => {
    it('should return correct provider name for a model', () => {
      service.setProviders(mockProviders);
      expect(service.providerForModel('claude-3-opus')).toBe('anthropic');
      expect(service.providerForModel('gpt-4o')).toBe('openai');
    });

    it('should return empty string for unknown model', () => {
      service.setProviders(mockProviders);
      expect(service.providerForModel('unknown-model')).toBe('');
    });
  });

  describe('switchModel()', () => {
    it('should optimistically update model and persist on success', async () => {
      service.setProviders(mockProviders);
      const promise = service.switchModel('conv-1', 'gpt-4o', 'test-token');

      const req = httpMock.expectOne('/api/sessions/conv-1/model?token=test-token');
      expect(req.request.method).toBe('PATCH');
      req.flush({});

      await promise;
      expect(service.selectedModel()).toBe('gpt-4o');
      expect(localStorage.getItem('preferred_model')).toBe('gpt-4o');
    });

    it('should revert model on HTTP error', async () => {
      service.setProviders(mockProviders);
      service.selectModel('claude-3-sonnet');

      const promise = service.switchModel('conv-1', 'gpt-4o', 'test-token');

      const req = httpMock.expectOne('/api/sessions/conv-1/model?token=test-token');
      req.error(new ErrorEvent('network error'));

      await promise;
      expect(service.selectedModel()).toBe('claude-3-sonnet');
    });
  });
});
