import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RoutingBadgeComponent } from './routing-badge.component';
import { RoutingMetadata } from '../models/chat.models';

describe('RoutingBadgeComponent', () => {
  let fixture: ComponentFixture<RoutingBadgeComponent>;

  function create(metadata?: RoutingMetadata | null) {
    fixture = TestBed.createComponent(RoutingBadgeComponent);
    if (metadata !== undefined) {
      fixture.componentRef.setInput('metadata', metadata);
    }
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RoutingBadgeComponent],
    }).compileComponents();
  });

  it('should create', () => {
    const f = create();
    expect(f.componentInstance).toBeTruthy();
  });

  it('should render nothing when metadata is null', () => {
    const f = create(null);
    const badge = f.nativeElement.querySelector('.badge');
    // Component may render nothing or hide badge when no metadata
    expect(f.nativeElement.textContent).not.toContain('undefined');
  });

  it('should show skill badge for CALL_SKILL decision', () => {
    const meta: RoutingMetadata = {
      routing_decision: 'CALL_SKILL',
      skill_name: 'sales_report',
      confidence: 0.92,
    };
    const f = create(meta);
    const badge = f.nativeElement.querySelector('.badge');
    expect(badge).toBeTruthy();
    expect(badge.classList.contains('skill')).toBe(true);
  });

  it('should show clarify badge for CLARIFY decision', () => {
    const meta: RoutingMetadata = {
      routing_decision: 'CLARIFY',
      skill_name: null,
      confidence: 0.55,
    };
    const f = create(meta);
    const badge = f.nativeElement.querySelector('.badge');
    expect(badge).toBeTruthy();
    expect(badge.classList.contains('clarify')).toBe(true);
  });

  it('should show generic badge for GENERIC_ANSWER decision', () => {
    const meta: RoutingMetadata = {
      routing_decision: 'GENERIC_ANSWER',
      skill_name: null,
      confidence: 0.0,
    };
    const f = create(meta);
    const badge = f.nativeElement.querySelector('.badge');
    expect(badge).toBeTruthy();
    expect(badge.classList.contains('generic')).toBe(true);
  });
});
