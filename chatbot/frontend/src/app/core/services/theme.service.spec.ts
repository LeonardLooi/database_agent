import { TestBed } from '@angular/core/testing';
import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  let service: ThemeService;

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    TestBed.configureTestingModule({ providers: [ThemeService] });
    service = TestBed.inject(ThemeService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should create', () => {
    expect(service).toBeTruthy();
  });

  it('should apply data-theme attribute on init', () => {
    const theme = document.documentElement.getAttribute('data-theme');
    expect(['dark', 'light']).toContain(theme as string);
  });

  it('should persist dark preference in localStorage', () => {
    localStorage.setItem('preferred-theme', 'dark');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [ThemeService] });
    const newService = TestBed.inject(ThemeService);
    expect(newService.isDark()).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('should persist light preference in localStorage', () => {
    localStorage.setItem('preferred-theme', 'light');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [ThemeService] });
    const newService = TestBed.inject(ThemeService);
    expect(newService.isDark()).toBe(false);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  describe('toggle()', () => {
    it('should toggle from light to dark', () => {
      localStorage.setItem('preferred-theme', 'light');
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({ providers: [ThemeService] });
      const svc = TestBed.inject(ThemeService);
      expect(svc.isDark()).toBe(false);

      svc.toggle();

      expect(svc.isDark()).toBe(true);
      expect(localStorage.getItem('preferred-theme')).toBe('dark');
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    });

    it('should toggle from dark to light', () => {
      localStorage.setItem('preferred-theme', 'dark');
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({ providers: [ThemeService] });
      const svc = TestBed.inject(ThemeService);
      expect(svc.isDark()).toBe(true);

      svc.toggle();

      expect(svc.isDark()).toBe(false);
      expect(localStorage.getItem('preferred-theme')).toBe('light');
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });
  });
});
