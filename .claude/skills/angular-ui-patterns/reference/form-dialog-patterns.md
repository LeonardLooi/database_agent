# Form Patterns & Dialog/Modal Patterns

## Form Patterns

### Form with Loading and Validation

```typescript
@Component({
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <div class="form-field">
        <label for="name">Name</label>
        <input
          id="name"
          formControlName="name"
          [class.error]="isFieldInvalid('name')"
        />
        @if (isFieldInvalid("name")) {
          <span class="error-text">
            {{ getFieldError("name") }}
          </span>
        }
      </div>

      <div class="form-field">
        <label for="email">Email</label>
        <input id="email" type="email" formControlName="email" />
        @if (isFieldInvalid("email")) {
          <span class="error-text">
            {{ getFieldError("email") }}
          </span>
        }
      </div>

      <button type="submit" [disabled]="form.invalid || submitting()">
        @if (submitting()) {
          <app-spinner size="sm" /> Submitting...
        } @else {
          Submit
        }
      </button>
    </form>
  `,
})
export class UserFormComponent {
  private fb = inject(FormBuilder);

  submitting = signal(false);

  form = this.fb.group({
    name: ["", [Validators.required, Validators.minLength(2)]],
    email: ["", [Validators.required, Validators.email]],
  });

  isFieldInvalid(field: string): boolean {
    const control = this.form.get(field);
    return control ? control.invalid && control.touched : false;
  }

  getFieldError(field: string): string {
    const control = this.form.get(field);
    if (control?.hasError("required")) return "This field is required";
    if (control?.hasError("email")) return "Invalid email format";
    if (control?.hasError("minlength")) return "Too short";
    return "";
  }

  async onSubmit() {
    if (this.form.invalid) return;

    this.submitting.set(true);
    try {
      await this.service.submit(this.form.value);
      this.toast.success("Submitted successfully");
    } catch {
      this.toast.error("Submission failed");
    } finally {
      this.submitting.set(false);
    }
  }
}
```

---

## Dialog/Modal Patterns

### Confirmation Dialog Service Pattern

```typescript
// dialog.service.ts
@Injectable({ providedIn: 'root' })
export class DialogService {
  private dialog = inject(Dialog); // CDK Dialog or custom

  async confirm(options: {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
  }): Promise<boolean> {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: options,
    });

    return await firstValueFrom(dialogRef.closed) ?? false;
  }
}

// Usage
async deleteItem(item: Item) {
  const confirmed = await this.dialog.confirm({
    title: 'Delete Item',
    message: `Are you sure you want to delete "${item.name}"?`,
    confirmText: 'Delete',
  });

  if (confirmed) {
    await this.store.delete(item.id);
  }
}
```
