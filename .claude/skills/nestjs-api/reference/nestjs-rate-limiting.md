# Inbound Rate Limiting — NestJS

## Layer 1: GCP Cloud Armor (Edge)

Configure Cloud Armor security policy on the GCP Load Balancer in front of Cloud Run.
See `java-spring-api/reference/spring-boot-rate-limiting.md` for Terraform example.

Key settings:
- 100 req/min per IP baseline
- OWASP ModSecurity CRS enabled
- Geo-blocking for non-target regions

## Layer 2: @nestjs/throttler with Redis (Application)

For multi-instance Cloud Run deployments, use Redis-backed storage so all instances share rate limit state.

Install:

```bash
npm install @nestjs/throttler @nestjs/throttler-storage-redis ioredis
```

Module config:

```typescript
import { ThrottlerModule } from '@nestjs/throttler';
import { ThrottlerStorageRedisService } from '@nestjs/throttler-storage-redis';
import Redis from 'ioredis';

@Module({
  imports: [
    ThrottlerModule.forRoot({
      throttlers: [
        { name: 'short', ttl: 1000, limit: 10 },    // 10/sec burst
        { name: 'medium', ttl: 10000, limit: 50 },   // 50/10sec
        { name: 'long', ttl: 60000, limit: 200 },    // 200/min sustained
      ],
      storage: new ThrottlerStorageRedisService(
        new Redis(process.env.REDIS_URL),
      ),
    }),
  ],
})
export class AppModule {}
```

## Auth Endpoint Stricter Limits

```typescript
@Throttle({ short: { limit: 5, ttl: 60000 } })  // 5/min
@Post('login')
async login(@Body() dto: LoginDto) { ... }

@Throttle({ short: { limit: 3, ttl: 3600000 } }) // 3/hour
@Post('forgot-password')
async forgotPassword(@Body() dto: ForgotPasswordDto) { ... }

@Throttle({ short: { limit: 3, ttl: 3600000 } }) // 3/hour
@Post('register')
async register(@Body() dto: RegisterDto) { ... }
```

## Key Rules

- ALWAYS use Redis storage for Cloud Run (multiple instances share state)
- Edge rate limiting (Cloud Armor) catches volumetric attacks before they hit your app
- Application rate limiting (@nestjs/throttler) catches per-route abuse patterns
- Track password reset by email, not just IP
- In-memory throttling (default) is only suitable for single-instance dev environments
