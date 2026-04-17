# NestJS Security — Authentication & Authorization

Enterprise authentication patterns for NestJS 11.x with JWT, bcrypt, and rate limiting.

## Redirect URL Validation

### Allowlist-Based Redirect Guard

Open redirects allow attackers to craft URLs like `yourapp.com/login?redirect=evil.com` that look legitimate but send users to phishing sites. Always validate redirect targets against an allowlist.

```typescript
// src/common/guards/safe-redirect.guard.ts
import { Injectable, BadRequestException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class SafeRedirectService {
  private readonly allowedHosts: Set<string>;

  constructor(private readonly config: ConfigService) {
    // Load allowed redirect hosts from config
    this.allowedHosts = new Set(
      this.config.get<string>('ALLOWED_REDIRECT_HOSTS', '')
        .split(',')
        .filter(Boolean)
        .map((h) => h.trim().toLowerCase()),
    );
  }

  /**
   * Validate a redirect URL against the allowlist.
   * Returns the URL if safe, throws if not.
   */
  validateRedirectUrl(redirectUrl: string): string {
    // Allow relative paths (they stay on the same origin)
    if (redirectUrl.startsWith('/') && !redirectUrl.startsWith('//')) {
      return redirectUrl;
    }

    try {
      const parsed = new URL(redirectUrl);
      if (!this.allowedHosts.has(parsed.hostname.toLowerCase())) {
        throw new BadRequestException(
          `Redirect to '${parsed.hostname}' is not allowed`,
        );
      }
      // Block non-HTTPS redirects in production
      if (parsed.protocol !== 'https:') {
        throw new BadRequestException('Only HTTPS redirects are allowed');
      }
      return redirectUrl;
    } catch (e) {
      if (e instanceof BadRequestException) throw e;
      throw new BadRequestException('Invalid redirect URL');
    }
  }
}
```

### Usage in Auth Controller

```typescript
@Post('login')
async login(
  @Body() dto: LoginDto,
  @Query('redirect') redirect?: string,
) {
  const tokens = await this.authService.login(dto);

  // Validate redirect URL if provided
  const safeRedirect = redirect
    ? this.safeRedirectService.validateRedirectUrl(redirect)
    : '/dashboard';

  return { ...tokens, redirectTo: safeRedirect };
}
```

### Key Rules
- **NEVER** redirect to a user-provided URL without validation
- Allow relative paths (`/dashboard`) — they stay on the same origin
- Block `//evil.com` (protocol-relative URLs that look like relative paths)
- Require HTTPS for absolute redirects
- Load allowed hosts from environment config, not hardcoded

---

## JWT Security Best Practices

### Installation

```bash
npm install @nestjs/jwt @nestjs/passport passport-jwt bcrypt
npm install --save-dev @types/passport-jwt @types/bcrypt
```

### JWT Strategy with RS256

```typescript
// src/features/auth/strategies/jwt.strategy.ts
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { readFileSync } from 'fs';
import { RedisService } from '@/common/redis/redis.service';

interface JwtPayload {
  sub: string;
  email: string;
  iat: number;
  exp: number;
  aud: string;
  iss: string;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private configService: ConfigService,
    private redisService: RedisService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: readFileSync(
        configService.get<string>('JWT_PUBLIC_KEY_PATH'),
        'utf8',
      ),
      algorithms: ['RS256'], // Use RS256 instead of HS256
      audience: configService.get<string>('JWT_AUDIENCE'),
      issuer: configService.get<string>('JWT_ISSUER'),
    });
  }

  async validate(payload: JwtPayload) {
    // Check token revocation via Redis blacklist
    const isBlacklisted = await this.redisService.get(
      `blacklist:${payload.sub}:${payload.iat}`,
    );

    if (isBlacklisted) {
      throw new UnauthorizedException('Token has been revoked');
    }

    return {
      userId: payload.sub,
      email: payload.email,
    };
  }
}
```

### Token Service

```typescript
// src/features/auth/services/token.service.ts
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { readFileSync } from 'fs';
import { RedisService } from '@/common/redis/redis.service';

@Injectable()
export class TokenService {
  constructor(
    private jwtService: JwtService,
    private configService: ConfigService,
    private redisService: RedisService,
  ) {}

  async generateAccessToken(userId: string, email: string): Promise<string> {
    const payload = {
      sub: userId,
      email,
      aud: this.configService.get<string>('JWT_AUDIENCE'),
      iss: this.configService.get<string>('JWT_ISSUER'),
    };

    return this.jwtService.sign(payload, {
      privateKey: readFileSync(
        this.configService.get<string>('JWT_PRIVATE_KEY_PATH'),
        'utf8',
      ),
      algorithm: 'RS256',
      expiresIn: '15m', // Short-lived access token
    });
  }

  async generateRefreshToken(userId: string): Promise<string> {
    return this.jwtService.sign(
      { sub: userId },
      {
        privateKey: readFileSync(
          this.configService.get<string>('JWT_PRIVATE_KEY_PATH'),
          'utf8',
        ),
        algorithm: 'RS256',
        expiresIn: '7d', // Long-lived refresh token
      },
    );
  }

  async revokeToken(userId: string, iat: number): Promise<void> {
    // Add to Redis blacklist with TTL matching token expiry
    await this.redisService.set(
      `blacklist:${userId}:${iat}`,
      'revoked',
      15 * 60, // 15 minutes
    );
  }
}
```

### Password Hashing

```typescript
// src/features/auth/services/password.service.ts
import { Injectable } from '@nestjs/common';
import * as bcrypt from 'bcrypt';

@Injectable()
export class PasswordService {
  private readonly SALT_ROUNDS = 12; // Cost factor for bcrypt

  async hash(password: string): Promise<string> {
    return bcrypt.hash(password, this.SALT_ROUNDS);
  }

  async compare(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }
}
```

### Rate Limiting on Auth Endpoints

```typescript
// src/features/auth/controllers/auth.controller.ts
import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { Throttle } from '@nestjs/throttler';

@Controller('auth')
export class AuthController {
  // Stricter rate limiting: 5 requests per 15 minutes
  @Throttle({ default: { limit: 5, ttl: 900000 } })
  @Post('login')
  async login(@Body() loginDto: LoginDto) {
    // Login logic
  }

  @Throttle({ default: { limit: 3, ttl: 3600000 } }) // 3 per hour
  @Post('forgot-password')
  async forgotPassword(@Body() forgotPasswordDto: ForgotPasswordDto) {
    // Forgot password logic
  }
}
```

## Rate Limiting Deep Dive

### Installation

```bash
npm install @nestjs/throttler
```

### Multi-Tier Rate Limiting

```typescript
// src/common/throttler/throttler.config.ts
import { ThrottlerModuleOptions } from '@nestjs/throttler';
import { ConfigService } from '@nestjs/config';

export const getThrottlerConfig = (
  configService: ConfigService,
): ThrottlerModuleOptions => ({
  throttlers: [
    {
      name: 'short',
      ttl: 1000, // 1 second
      limit: 10, // 10 requests per second
    },
    {
      name: 'medium',
      ttl: 60000, // 1 minute
      limit: 100, // 100 requests per minute
    },
    {
      name: 'long',
      ttl: 3600000, // 1 hour
      limit: 1000, // 1000 requests per hour
    },
  ],
  storage: configService.get('REDIS_URL')
    ? require('@nestjs/throttler-storage-redis').ThrottlerStorageRedisService
    : undefined,
});
```

### Custom Throttler Guard

```typescript
// src/common/throttler/custom-throttler.guard.ts
import { Injectable, ExecutionContext } from '@nestjs/common';
import { ThrottlerGuard, ThrottlerException } from '@nestjs/throttler';
import { FastifyRequest } from 'fastify';

@Injectable()
export class CustomThrottlerGuard extends ThrottlerGuard {
  // Override to use user ID instead of IP for authenticated routes
  protected async getTracker(req: FastifyRequest): Promise<string> {
    const user = req['user'];

    // Use user ID for authenticated requests
    if (user?.userId) {
      return `user:${user.userId}`;
    }

    // Fall back to IP for unauthenticated requests
    return req.ip || 'unknown';
  }

  // Custom error message
  protected throwThrottlingException(context: ExecutionContext): void {
    throw new ThrottlerException(
      'Rate limit exceeded. Please try again later.',
    );
  }
}
```

### Per-Endpoint Configuration

```typescript
// src/features/auth/controllers/auth.controller.ts
import { Controller, Post, UseGuards } from '@nestjs/common';
import { SkipThrottle, Throttle } from '@nestjs/throttler';
import { CustomThrottlerGuard } from '@/common/throttler/custom-throttler.guard';

@Controller('auth')
@UseGuards(CustomThrottlerGuard)
export class AuthController {
  // Very strict: 5 attempts per 15 minutes
  @Throttle({ short: { limit: 5, ttl: 900000 } })
  @Post('login')
  async login() {}

  // Moderate: 3 attempts per hour
  @Throttle({ medium: { limit: 3, ttl: 3600000 } })
  @Post('forgot-password')
  async forgotPassword() {}

  // Skip throttling for health check
  @SkipThrottle()
  @Post('health')
  async health() {}
}
```

---

## Webhook Signature Verification

**NEVER** process webhook payloads without verifying the signature. Attackers can forge webhook calls to trigger payments, refunds, or state changes.

### Stripe Example

```typescript
// webhook.controller.ts
import Stripe from 'stripe';

@Controller('webhooks')
export class WebhookController {
  private readonly logger = new Logger(WebhookController.name);
  private readonly stripe: Stripe;

  constructor(private readonly config: ConfigService) {
    this.stripe = new Stripe(this.config.getOrThrow('STRIPE_SECRET_KEY'));
  }

  @Post('stripe')
  async handleStripeWebhook(
    @Headers('stripe-signature') signature: string,
    @Req() req: RawBodyRequest<FastifyRequest>,
  ) {
    const webhookSecret = this.config.getOrThrow('STRIPE_WEBHOOK_SECRET');

    let event: Stripe.Event;
    try {
      event = this.stripe.webhooks.constructEvent(
        req.rawBody,        // Raw body buffer — NOT parsed JSON
        signature,
        webhookSecret,
      );
    } catch (err) {
      this.logger.error('Webhook signature verification failed', err);
      throw new BadRequestException('Invalid webhook signature');
    }

    this.logger.log(`Webhook received: ${event.type} (${event.id})`);

    switch (event.type) {
      case 'checkout.session.completed':
        await this.handleCheckoutComplete(event.data.object);
        break;
      case 'invoice.payment_failed':
        await this.handlePaymentFailed(event.data.object);
        break;
      default:
        this.logger.log(`Unhandled event type: ${event.type}`);
    }

    return { received: true };
  }
}
```

### Fastify Raw Body Setup

```typescript
// main.ts — required for Stripe signature verification
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter(),
  { rawBody: true },  // Enable raw body access
);
```

### Generic HMAC Verification (Non-Stripe Providers)

```typescript
import { createHmac, timingSafeEqual } from 'crypto';

function verifyWebhookSignature(
  payload: Buffer,
  signature: string,
  secret: string,
): boolean {
  const expected = createHmac('sha256', secret).update(payload).digest('hex');
  return timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

### Key Rules

- ALWAYS use `rawBody` (Buffer), never parsed JSON, for signature verification
- Use `timingSafeEqual` to prevent timing attacks on signature comparison
- Store webhook secrets in environment variables, never hardcoded
- Log webhook events for audit trail
- Return 200 quickly — do heavy processing async (queue)
- **NEVER point dev/test webhook URLs to production endpoints.** Use provider sandbox/test modes (Stripe test mode, PayPal sandbox). Each environment (dev, staging, prod) must have its own webhook URL and its own webhook secret. Shared secrets across environments = one compromised env compromises all.
