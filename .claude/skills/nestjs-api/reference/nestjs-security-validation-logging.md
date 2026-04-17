# NestJS Security — Validation, Logging & Prisma

Input validation hardening, PII masking in logs, Prisma security patterns, and OWASP checklist for NestJS 11.x. For dependency scanning, headers, and CORS, see `nestjs-security-scanning.md`.

**Note:** For authentication and authorization patterns (JWT, passwords, rate limiting), see `nestjs-security-auth.md`.

## 1. Input Validation Hardening

### Advanced DTO Validation

```typescript
// src/features/users/dto/create-user.dto.ts
import {
  IsEmail,
  IsString,
  IsNotEmpty,
  MinLength,
  MaxLength,
  Matches,
  IsOptional,
  ValidateNested,
  IsArray,
  ArrayMaxSize,
} from 'class-validator';
import { Transform, Type } from 'class-transformer';
import * as DOMPurify from 'isomorphic-dompurify';

export class CreateUserDto {
  @IsEmail({}, { message: 'Invalid email format' })
  @MaxLength(255)
  email: string;

  @IsString()
  @MinLength(12, { message: 'Password must be at least 12 characters' })
  @MaxLength(128)
  @Matches(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]+$/,
    {
      message: 'Password must contain uppercase, lowercase, number, and special character',
    },
  )
  password: string;

  @IsString()
  @IsNotEmpty()
  @MinLength(2)
  @MaxLength(50)
  @Matches(/^[a-zA-Z\s'-]+$/, { message: 'Name contains invalid characters' })
  @Transform(({ value }) => DOMPurify.sanitize(value.trim()))
  firstName: string;

  @IsArray()
  @ArrayMaxSize(10)
  @IsString({ each: true })
  tags: string[];
}
```

### Global Validation Pipe

```typescript
// src/main.ts
import { ValidationPipe } from '@nestjs/common';

app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
    disableErrorMessages: process.env.NODE_ENV === 'production',
  }),
);
```

## 2. Secure Logging — PII Masking

### Log Sanitizer Service

```typescript
// src/common/logging/log-sanitizer.service.ts
import { Injectable } from '@nestjs/common';

@Injectable()
export class LogSanitizerService {
  private readonly sensitivePatterns = [
    { pattern: /"password":\s*"[^"]*"/gi, replacement: '"password":"***MASKED***"' },
    { pattern: /"token":\s*"[^"]*"/gi, replacement: '"token":"***MASKED***"' },
    { pattern: /\b\d{3}-\d{2}-\d{4}\b/g, replacement: '***-**-****' }, // SSN
    { pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, replacement: '****-****-****-****' }, // Credit card
  ];

  sanitize(data: unknown): unknown {
    if (typeof data === 'string') {
      return this.sanitizeString(data);
    }
    if (Array.isArray(data)) {
      return data.map((item) => this.sanitize(item));
    }
    if (typeof data === 'object' && data !== null) {
      return this.sanitizeObject(data);
    }
    return data;
  }

  private sanitizeString(str: string): string {
    let sanitized = str;
    for (const { pattern, replacement } of this.sensitivePatterns) {
      sanitized = sanitized.replace(pattern, replacement);
    }
    return sanitized;
  }

  private sanitizeObject(obj: Record<string, unknown>): Record<string, unknown> {
    const sanitized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj)) {
      sanitized[key] = this.isSensitiveKey(key) ? this.maskValue(value) : this.sanitize(value);
    }
    return sanitized;
  }

  private isSensitiveKey(key: string): boolean {
    const sensitiveKeys = ['password', 'token', 'apiKey', 'secret', 'ssn', 'creditCard'];
    return sensitiveKeys.some((s) => key.toLowerCase().includes(s.toLowerCase()));
  }

  private maskValue(value: unknown): string {
    if (typeof value !== 'string' || value.length <= 4) return '***';
    return `${value.substring(0, 2)}***${value.substring(value.length - 2)}`;
  }
}
```

## 3. Prisma Security

### Avoid SQL Injection

```typescript
// ❌ DANGEROUS
async findUserBad(email: string) {
  return this.prisma.$queryRaw`SELECT * FROM users WHERE email = ${email}`;
}

// ✅ SAFE — Parameterized query
import { Prisma } from '@prisma/client';

async findUserSafe(email: string) {
  return this.prisma.$queryRaw(
    Prisma.sql`SELECT * FROM users WHERE email = ${email}`,
  );
}

// ✅ BEST — Use Prisma Client methods
async findUserBest(email: string) {
  return this.prisma.user.findUnique({ where: { email } });
}
```

### Field-Level Encryption

```typescript
// src/common/encryption/encryption.service.ts
import { Injectable } from '@nestjs/common';
import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'crypto';

@Injectable()
export class EncryptionService {
  private readonly algorithm = 'aes-256-gcm';
  private readonly key: Buffer;

  constructor() {
    this.key = scryptSync(process.env.ENCRYPTION_KEY, 'salt', 32);
  }

  encrypt(text: string): string {
    const iv = randomBytes(16);
    const cipher = createCipheriv(this.algorithm, this.key, iv);
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    const authTag = cipher.getAuthTag();
    return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
  }

  decrypt(encryptedText: string): string {
    const [ivHex, authTagHex, encrypted] = encryptedText.split(':');
    const iv = Buffer.from(ivHex, 'hex');
    const authTag = Buffer.from(authTagHex, 'hex');
    const decipher = createDecipheriv(this.algorithm, this.key, iv);
    decipher.setAuthTag(authTag);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  }
}
```

### Soft Delete Pattern

```typescript
// prisma/schema.prisma
model User {
  id        String    @id @default(uuid())
  email     String    @unique
  deletedAt DateTime? @map("deleted_at")

  @@map("users")
}

// Repository
@Injectable()
export class UserRepository {
  constructor(private prisma: PrismaService) {}

  async softDelete(id: string): Promise<void> {
    await this.prisma.user.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }

  async findActive(id: string) {
    return this.prisma.user.findFirst({
      where: { id, deletedAt: null },
    });
  }
}
```

## 4. Security Checklist

### OWASP Top 10 Mitigations

- [ ] **A01: Broken Access Control** — Implement RBAC with guards on protected routes
- [ ] **A02: Cryptographic Failures** — Use bcrypt (cost >=12), RS256 for JWT, encrypt sensitive DB fields
- [ ] **A03: Injection** — Never use string concatenation in queries, validate all inputs with DTOs
- [ ] **A04: Insecure Design** — Implement rate limiting, circuit breakers, fail-fast config
- [ ] **A05: Security Misconfiguration** — Run npm audit in CI/CD, configure Helmet, disable stack traces in prod
- [ ] **A06: Vulnerable Components** — Automate dependency scanning (Snyk), keep dependencies updated
- [ ] **A07: Auth Failures** — Short-lived tokens (15 min), refresh token rotation, token revocation, rate limit auth endpoints
- [ ] **A08: Data Integrity Failures** — Verify JWT claims, use integrity checks, implement audit logging
- [ ] **A09: Logging Failures** — Mask PII in logs, log all auth attempts, centralized logging, alerting
- [ ] **A10: SSRF** — Validate/sanitize URLs, whitelist allowed domains, use circuit breakers

### Additional Measures

- [ ] Enable CORS with explicit origin whitelist
- [ ] Implement CSP to prevent XSS
- [ ] Use `whitelist: true` in ValidationPipe
- [ ] Soft delete pattern to prevent data loss
- [ ] Field-level encryption for sensitive data
- [ ] Automated security scanning in CI/CD
- [ ] Regular penetration testing

---

**Next Steps:**
1. Run security scan: `bash security-scan.sh`
2. Configure ESLint security rules: `npm run lint`
3. Review and apply all checklist items
4. Set up automated security audits in CI/CD
