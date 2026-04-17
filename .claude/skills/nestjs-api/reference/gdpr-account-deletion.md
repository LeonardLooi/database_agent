# GDPR Account Deletion Pattern — NestJS

## Overview

GDPR Article 17 (Right to Erasure) requires a complete account deletion flow. Users must be able to request deletion, confirm it, and have all PII removed within 30 days.

## Flow

1. User requests deletion -> creates a `DeletionRequest` record with 7-day grace period
2. Confirmation email sent with cancel link
3. After grace period expires, background job processes deletion
4. All PII anonymized or hard-deleted; non-PII audit records retained with anonymized references

## Prisma Schema

```prisma
model DeletionRequest {
  id          String          @id @default(uuid())
  userId      String          @unique
  requestedAt DateTime        @default(now())
  scheduledAt DateTime        // requestedAt + 7 days
  status      DeletionStatus  @default(PENDING)
  processedAt DateTime?
  user        User            @relation(fields: [userId], references: [id])
}

enum DeletionStatus {
  PENDING
  CANCELLED
  PROCESSING
  COMPLETED
}
```

## Service Pattern

```typescript
@Injectable()
export class AccountDeletionService {
  private readonly logger = new Logger(AccountDeletionService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly emailService: EmailService,
  ) {}

  async requestDeletion(userId: string): Promise<DeletionRequest> {
    const user = await this.prisma.user.findUniqueOrThrow({ where: { id: userId } });
    const scheduledAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);

    const request = await this.prisma.deletionRequest.create({
      data: { userId, scheduledAt },
    });

    await this.emailService.sendTransactional(
      user.email,
      'Account Deletion Scheduled',
      `Your account will be deleted on ${scheduledAt.toISOString()}. Cancel: <link>`,
    );

    this.logger.log(`Deletion requested for user ${userId}, scheduled ${scheduledAt}`);
    return request;
  }

  async cancelDeletion(userId: string): Promise<void> {
    await this.prisma.deletionRequest.update({
      where: { userId },
      data: { status: 'CANCELLED' },
    });
    this.logger.log(`Deletion cancelled for user ${userId}`);
  }

  async processPendingDeletions(): Promise<void> {
    const due = await this.prisma.deletionRequest.findMany({
      where: { status: 'PENDING', scheduledAt: { lte: new Date() } },
    });

    for (const request of due) {
      await this.prisma.$transaction(async (tx) => {
        // 1. Anonymize PII in audit logs
        await tx.auditLog.updateMany({
          where: { userId: request.userId },
          data: { userId: 'DELETED_USER', userEmail: null },
        });
        // 2. Delete user data (cascade handles related records)
        await tx.user.delete({ where: { id: request.userId } });
        // 3. Mark deletion complete
        await tx.deletionRequest.update({
          where: { id: request.id },
          data: { status: 'COMPLETED', processedAt: new Date() },
        });
      });
      this.logger.log(`Deletion completed for user ${request.userId}`);
    }
  }
}
```

## Cron Job

```typescript
@Cron(CronExpression.EVERY_HOUR)
async handlePendingDeletions() {
  await this.accountDeletionService.processPendingDeletions();
}
```

## Checklist

- [ ] Deletion request endpoint exists (POST /api/v1/account/delete)
- [ ] Confirmation email sent with cancel link
- [ ] 7-day grace period before processing
- [ ] Cancel endpoint exists (POST /api/v1/account/delete/cancel)
- [ ] PII anonymized in audit logs (not hard-deleted)
- [ ] User record and related data cascade-deleted
- [ ] Background job processes expired requests
- [ ] Firebase Auth user deleted (if using Firebase)
- [ ] External service data deleted (Stripe customer, etc.)
