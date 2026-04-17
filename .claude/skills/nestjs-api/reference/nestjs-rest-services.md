# NestJS REST Services

Service layer patterns, external API integration, and data transformation for NestJS 11.x with circuit breaker resilience.

## 1. Service Layer Implementation

### Service with Pagination

```typescript
import { Injectable } from '@nestjs/common';
import { ProductRepository } from './product.repository';
import { ProductFilterDto, ProductResponseDto } from './dto';
import { PaginatedResponse } from '@/common/dto/paginated-response.dto';

@Injectable()
export class ProductService {
  constructor(private readonly repository: ProductRepository) {}

  async findAll(filter: ProductFilterDto): Promise<PaginatedResponse<ProductResponseDto>> {
    const [products, total] = await this.repository.findManyWithPagination(filter);

    const data = ProductResponseDto.fromEntityList(products);

    return PaginatedResponse.create(data, total, filter.page, filter.limit);
  }
}
```

---

## 2. External Service Client Pattern

### Complete HTTP Client with Circuit Breaker

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { ResilienceOrchestratorService } from '@/core/resilience/resilience-orchestrator.service';
import { ServiceUnavailableException } from '@/common/exceptions/service-unavailable.exception';

export interface PaymentRequest {
  orderId: string;
  amount: number;
  currency: string;
  customerId: string;
}

export interface PaymentResponse {
  transactionId: string;
  status: 'SUCCESS' | 'PENDING' | 'FAILED';
  amount: number;
  currency: string;
  processedAt: Date;
}

@Injectable()
export class PaymentServiceClient {
  private readonly logger = new Logger(PaymentServiceClient.name);
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly timeout: number;

  constructor(
    private readonly httpService: HttpService,
    private readonly resilienceOrchestrator: ResilienceOrchestratorService,
    private readonly configService: ConfigService,
  ) {
    this.baseUrl = this.configService.get<string>('paymentService.baseUrl')!;
    this.apiKey = this.configService.get<string>('paymentService.apiKey')!;
    this.timeout = this.configService.get<number>('paymentService.timeout', 5000);
  }

  async processPayment(request: PaymentRequest): Promise<PaymentResponse> {
    return this.resilienceOrchestrator.execute(
      'payment-service',
      () => this.doProcessPayment(request),
    );
  }

  private async doProcessPayment(request: PaymentRequest): Promise<PaymentResponse> {
    const url = `${this.baseUrl}/v1/payments`;

    try {
      const response = await firstValueFrom(
        this.httpService.post<PaymentResponse>(url, request, {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: this.timeout,
        })
      );

      this.logger.log(`Payment processed: ${response.data.transactionId}`);
      return response.data;

    } catch (error: any) {
      if (error.response) {
        const status = error.response.status;
        const data = error.response.data;

        // 4xx = client error (bad request, validation failed)
        if (status >= 400 && status < 500) {
          this.logger.error(`Payment client error: ${status}`, data);
          throw new Error(`Payment validation failed: ${data.message || 'Invalid request'}`);
        }

        // 5xx = service unavailable (triggers circuit breaker)
        if (status >= 500) {
          this.logger.error(`Payment service error: ${status}`, data);
          throw new ServiceUnavailableException('Payment service is unavailable');
        }
      }

      // Network error, timeout, etc.
      this.logger.error('Payment service network error', error.message);
      throw new ServiceUnavailableException('Failed to connect to payment service');
    }
  }

  async getPaymentStatus(transactionId: string): Promise<PaymentResponse> {
    return this.resilienceOrchestrator.execute(
      'payment-service',
      () => this.doGetPaymentStatus(transactionId),
    );
  }

  private async doGetPaymentStatus(transactionId: string): Promise<PaymentResponse> {
    const url = `${this.baseUrl}/v1/payments/${transactionId}`;

    try {
      const response = await firstValueFrom(
        this.httpService.get<PaymentResponse>(url, {
          headers: { 'Authorization': `Bearer ${this.apiKey}` },
          timeout: this.timeout,
        })
      );

      return response.data;

    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error(`Payment transaction not found: ${transactionId}`);
      }
      throw new ServiceUnavailableException('Payment service is unavailable');
    }
  }
}
```

---

## 3. Type-Safe Configuration for External Services

### Configuration Schema

```typescript
import { registerAs } from '@nestjs/config';

export interface PaymentServiceConfig {
  baseUrl: string;
  apiKey: string;
  timeout: number;
  retryAttempts: number;
}

export default registerAs('paymentService', (): PaymentServiceConfig => {
  const baseUrl = process.env.PAYMENT_SERVICE_BASE_URL;
  const apiKey = process.env.PAYMENT_SERVICE_API_KEY;

  if (!baseUrl || !apiKey) {
    throw new Error('PAYMENT_SERVICE_BASE_URL and PAYMENT_SERVICE_API_KEY are required');
  }

  return {
    baseUrl,
    apiKey,
    timeout: parseInt(process.env.PAYMENT_SERVICE_TIMEOUT ?? '5000', 10),
    retryAttempts: parseInt(process.env.PAYMENT_SERVICE_RETRY_ATTEMPTS ?? '3', 10),
  };
});
```

---

## 4. Bulk Operations

### Bulk Create

```typescript
@Injectable()
export class ProductService {
  async bulkCreate(dtos: CreateProductDto[]): Promise<{ count: number }> {
    const data = dtos.map(dto => ({
      name: dto.name,
      sku: dto.sku,
      price: new Prisma.Decimal(dto.price),
      status: dto.status ?? 'ACTIVE',
    }));

    const result = await this.prisma.product.createMany({
      data,
      skipDuplicates: true, // Skip records with duplicate unique fields
    });

    return { count: result.count };
  }
}
```

### Bulk Update with Transaction

```typescript
@Injectable()
export class ProductService {
  async bulkUpdateStatus(ids: string[], status: ProductStatus): Promise<{ count: number }> {
    const result = await this.prisma.product.updateMany({
      where: { id: { in: ids } },
      data: { status, updatedAt: new Date() },
    });

    return { count: result.count };
  }

  async bulkUpdatePrices(updates: Array<{ id: string; price: number }>): Promise<void> {
    await this.prisma.$transaction(
      updates.map(({ id, price }) =>
        this.prisma.product.update({
          where: { id },
          data: { price: new Prisma.Decimal(price) },
        })
      )
    );
  }
}
```

---

## 5. Soft Delete Pattern

### Prisma Middleware for Soft Delete

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit {
  async onModuleInit() {
    await this.$connect();
    this.applySoftDeleteMiddleware();
  }

  private applySoftDeleteMiddleware() {
    this.$use(async (params, next) => {
      // Intercept delete and convert to soft delete
      if (params.action === 'delete') {
        params.action = 'update';
        params.args['data'] = { deletedAt: new Date() };
      }

      if (params.action === 'deleteMany') {
        params.action = 'updateMany';
        if (params.args.data !== undefined) {
          params.args.data['deletedAt'] = new Date();
        } else {
          params.args['data'] = { deletedAt: new Date() };
        }
      }

      // Exclude soft-deleted records from queries
      if (params.action === 'findUnique' || params.action === 'findFirst') {
        params.action = 'findFirst';
        params.args.where = { ...params.args.where, deletedAt: null };
      }

      if (params.action === 'findMany') {
        if (params.args.where) {
          if (params.args.where.deletedAt === undefined) {
            params.args.where.deletedAt = null;
          }
        } else {
          params.args.where = { deletedAt: null };
        }
      }

      return next(params);
    });
  }
}
```

### Restore and Hard Delete

```typescript
@Injectable()
export class ProductService {
  async restore(id: string): Promise<ProductResponseDto> {
    const product = await this.prisma.product.update({
      where: { id },
      data: { deletedAt: null },
    });
    return ProductResponseDto.fromEntity(product);
  }

  async hardDelete(id: string): Promise<void> {
    await this.prisma.$executeRaw`DELETE FROM products WHERE id = ${id}`;
  }
}
```

---

## 6. Multi-Service Orchestration

### Service Composition Pattern

```typescript
@Injectable()
export class OrderService {
  constructor(
    private readonly paymentClient: PaymentServiceClient,
    private readonly inventoryClient: InventoryServiceClient,
    private readonly notificationClient: NotificationServiceClient,
    private readonly orderRepository: OrderRepository,
  ) {}

  async createOrder(dto: CreateOrderDto): Promise<OrderResponseDto> {
    // 1. Validate inventory availability
    const inventoryCheck = await this.inventoryClient.checkAvailability({
      items: dto.items,
    });

    if (!inventoryCheck.available) {
      throw new BadRequestException('Insufficient inventory');
    }

    // 2. Create order in pending state
    const order = await this.orderRepository.create({
      ...dto,
      status: 'PENDING',
    });

    try {
      // 3. Reserve inventory
      await this.inventoryClient.reserveItems({
        orderId: order.id,
        items: dto.items,
      });

      // 4. Process payment
      const paymentResult = await this.paymentClient.processPayment({
        orderId: order.id,
        amount: order.totalAmount,
        currency: 'USD',
        customerId: dto.customerId,
      });

      // 5. Update order status
      const confirmedOrder = await this.orderRepository.update(order.id, {
        status: 'CONFIRMED',
        paymentTransactionId: paymentResult.transactionId,
      });

      // 6. Send notification (fire-and-forget)
      this.notificationClient.sendOrderConfirmation({
        orderId: order.id,
        customerId: dto.customerId,
      }).catch(error => {
        // Log but don't fail the order
        this.logger.error('Failed to send notification', error);
      });

      return OrderResponseDto.fromEntity(confirmedOrder);

    } catch (error) {
      // Rollback: cancel order and release inventory
      await this.orderRepository.update(order.id, { status: 'CANCELLED' });
      await this.inventoryClient.releaseItems({ orderId: order.id });
      throw error;
    }
  }
}
```

---

## 7. Retry Logic with Exponential Backoff

### Retry Decorator

```typescript
export function Retry(options: {
  maxAttempts: number;
  delayMs: number;
  exponentialBackoff?: boolean;
}) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      let lastError: Error;
      for (let attempt = 1; attempt <= options.maxAttempts; attempt++) {
        try {
          return await originalMethod.apply(this, args);
        } catch (error) {
          lastError = error;
          if (attempt < options.maxAttempts) {
            const delay = options.exponentialBackoff
              ? options.delayMs * Math.pow(2, attempt - 1)
              : options.delayMs;
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        }
      }
      throw lastError;
    };

    return descriptor;
  };
}
```

### Usage

```typescript
@Injectable()
export class ExternalServiceClient {
  @Retry({ maxAttempts: 3, delayMs: 1000, exponentialBackoff: true })
  async fetchData(): Promise<Data> {
    return this.httpService.get('/api/data');
  }
}
```

---

## 8. Caching Strategy

### Service-Level Caching

```typescript
import { Injectable } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import { Cache } from 'cache-manager';
import { Inject } from '@nestjs/common';

@Injectable()
export class ProductService {
  constructor(
    @Inject(CACHE_MANAGER) private cacheManager: Cache,
    private readonly productRepository: ProductRepository,
  ) {}

  async findOne(id: string): Promise<ProductResponseDto> {
    const cacheKey = `product:${id}`;

    // Try cache first
    const cached = await this.cacheManager.get<ProductResponseDto>(cacheKey);
    if (cached) {
      return cached;
    }

    // Fetch from database
    const product = await this.productRepository.findById(id);
    if (!product) {
      throw new NotFoundException('Product not found');
    }

    const dto = ProductResponseDto.fromEntity(product);

    // Cache for 5 minutes
    await this.cacheManager.set(cacheKey, dto, 300000);

    return dto;
  }

  async update(id: string, dto: UpdateProductDto): Promise<ProductResponseDto> {
    const updated = await this.productRepository.update(id, dto);

    // Invalidate cache on update
    await this.cacheManager.del(`product:${id}`);

    return ProductResponseDto.fromEntity(updated);
  }
}
```

---

## 9. Implementation Checklist

- [ ] Prisma schema designed with proper relations and indexes
- [ ] Database migrations created and tested
- [ ] Feature module, controller, and service generated
- [ ] Request DTOs with `class-validator` validation
- [ ] Response DTOs with `@ApiProperty` for Swagger
- [ ] Pagination, filtering, and sorting implemented
- [ ] DTO mapping pattern chosen (factory, transformer, or mapper service)
- [ ] Repository layer with Prisma queries
- [ ] Service layer with business logic
- [ ] External service clients with circuit breaker
- [ ] Type-safe configuration for external APIs
- [ ] File upload endpoint with validation
- [ ] Bulk operations for create/update/delete
- [ ] Soft delete middleware configured
- [ ] API versioning strategy applied
- [ ] Swagger decorators on all endpoints
- [ ] OpenAPI JSON exported for API gateway
- [ ] Error responses follow RFC 9457 ProblemDetail
- [ ] Prisma errors mapped to HTTP status codes
- [ ] Unit tests for service methods
- [ ] Integration tests with supertest
- [ ] Contract tests for external APIs
- [ ] Environment variables validated at startup
- [ ] Logging added for audit trail
- [ ] Health check endpoint created
