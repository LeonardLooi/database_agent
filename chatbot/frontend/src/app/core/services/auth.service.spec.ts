import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [AuthService, provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should create', () => {
    expect(service).toBeTruthy();
  });

  it('should start with null token and userId', () => {
    expect(service.token()).toBeNull();
    expect(service.userId()).toBeNull();
  });

  describe('init()', () => {
    it('should use stored token if present in localStorage', async () => {
      localStorage.setItem('chatbot_auth_token', 'stored-token');
      await service.init();
      expect(service.token()).toBe('stored-token');
      // No HTTP request should be made
      httpMock.expectNone('/auth/guest');
    });

    it('should request a guest token when no stored token', async () => {
      const initPromise = service.init();
      const req = httpMock.expectOne('/auth/guest');
      expect(req.request.method).toBe('POST');
      req.flush({ access_token: 'new-token', token_type: 'bearer', user_id: 'guest_abc' });
      await initPromise;
      expect(service.token()).toBe('new-token');
      expect(service.userId()).toBe('guest_abc');
      expect(localStorage.getItem('chatbot_auth_token')).toBe('new-token');
    });

    it('should set fallback userId when guest token request fails', async () => {
      const initPromise = service.init();
      const req = httpMock.expectOne('/auth/guest');
      req.error(new ErrorEvent('network error'));
      await initPromise;
      expect(service.token()).toBeNull();
      expect(service.userId()).toMatch(/^guest_/);
    });
  });

  describe('clearToken()', () => {
    it('should clear token, userId, and localStorage', async () => {
      localStorage.setItem('chatbot_auth_token', 'some-token');
      service['token'].set('some-token');
      service['userId'].set('user_123');

      service.clearToken();

      expect(service.token()).toBeNull();
      expect(service.userId()).toBeNull();
      expect(localStorage.getItem('chatbot_auth_token')).toBeNull();
    });
  });
});
