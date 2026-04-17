# NestJS REST Controllers — Workflow & Swagger Setup

REST service development workflow and OpenAPI/Swagger-driven controller patterns for NestJS 11.x with Fastify and TypeScript 5.x.

## 1. REST Service Development Workflow

### Step-by-Step Process

1. **Gather Requirements**
   - Parse OpenAPI spec or requirement documents
   - Extract entities, relationships, and endpoint definitions
   - Identify DTOs, validation rules, and business logic

2. **Database Schema**
   - Design Prisma schema with proper relations
   - Run migrations: `npx prisma migrate dev`
   - Generate Prisma Client: `npx prisma generate`

3. **Generate Feature Module**
   ```bash
   nest g module features/products
   nest g controller features/products
   nest g service features/products
   ```

4. **Create DTOs**
   - Request DTOs with `class-validator` decorators
   - Response DTOs with `@ApiProperty` for Swagger
   - Reusable pagination and filter DTOs

5. **Implement Layers**
   - Repository: Prisma database access
   - Service: Business logic + external service calls with circuit breaker
   - Controller: HTTP endpoints with Swagger documentation

6. **Add Integrations**
   - External service clients with circuit breaker pattern
   - Type-safe configuration for API endpoints
   - Error mapping and retry logic

7. **Write Tests**
   - Unit tests for services and repositories
   - Integration tests with supertest
   - Contract tests for external APIs

8. **Configure Documentation**
   - Swagger decorators on controllers
   - Export OpenAPI JSON for API gateway
   - Add example requests/responses

---

## 2. OpenAPI/Swagger-Driven Development

### Controller with Complete Swagger Documentation

```typescript
import { Controller, Get, Post, Put, Delete, Body, Param, Query, HttpCode, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiQuery, ApiBody } from '@nestjs/swagger';
import { ProductService } from './product.service';
import { CreateProductDto, UpdateProductDto, ProductResponseDto, ProductFilterDto } from './dto';
import { PaginatedResponse } from '@/common/dto/paginated-response.dto';

@ApiTags('Products')
@Controller({ path: 'products', version: '1' })
export class ProductController {
  constructor(private readonly productService: ProductService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({
    summary: 'Create a new product',
    description: 'Creates a product with validation and returns the created entity'
  })
  @ApiBody({ type: CreateProductDto })
  @ApiResponse({
    status: 201,
    description: 'Product created successfully',
    type: ProductResponseDto
  })
  @ApiResponse({ status: 400, description: 'Invalid input data' })
  @ApiResponse({ status: 409, description: 'Product with SKU already exists' })
  async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
    const product = await this.productService.create(dto);
    return ProductResponseDto.fromEntity(product);
  }

  @Get()
  @ApiOperation({ summary: 'List products with pagination and filters' })
  @ApiQuery({ name: 'page', required: false, type: Number, example: 1 })
  @ApiQuery({ name: 'limit', required: false, type: Number, example: 20 })
  @ApiQuery({ name: 'search', required: false, type: String })
  @ApiQuery({ name: 'status', required: false, enum: ['ACTIVE', 'INACTIVE', 'ARCHIVED'] })
  @ApiResponse({
    status: 200,
    description: 'Paginated list of products',
    type: PaginatedResponse<ProductResponseDto>
  })
  async findAll(@Query() filter: ProductFilterDto): Promise<PaginatedResponse<ProductResponseDto>> {
    return this.productService.findAll(filter);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get product by ID' })
  @ApiParam({ name: 'id', description: 'Product UUID', example: '123e4567-e89b-12d3-a456-426614174000' })
  @ApiResponse({ status: 200, description: 'Product found', type: ProductResponseDto })
  @ApiResponse({ status: 404, description: 'Product not found' })
  async findOne(@Param('id') id: string): Promise<ProductResponseDto> {
    const product = await this.productService.findOne(id);
    return ProductResponseDto.fromEntity(product);
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update product' })
  @ApiParam({ name: 'id', description: 'Product UUID' })
  @ApiBody({ type: UpdateProductDto })
  @ApiResponse({ status: 200, description: 'Product updated', type: ProductResponseDto })
  @ApiResponse({ status: 404, description: 'Product not found' })
  async update(@Param('id') id: string, @Body() dto: UpdateProductDto): Promise<ProductResponseDto> {
    const product = await this.productService.update(id, dto);
    return ProductResponseDto.fromEntity(product);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete product (soft delete)' })
  @ApiParam({ name: 'id', description: 'Product UUID' })
  @ApiResponse({ status: 204, description: 'Product deleted' })
  @ApiResponse({ status: 404, description: 'Product not found' })
  async remove(@Param('id') id: string): Promise<void> {
    await this.productService.remove(id);
  }
}
```

### Swagger Setup in main.ts

```typescript
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, NestFastifyApplication } from '@nestjs/platform-fastify';
import { ValidationPipe, VersioningType } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { writeFileSync } from 'fs';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({ logger: true })
  );

  // Global validation pipe
  app.useGlobalPipes(new ValidationPipe({
    transform: true,
    whitelist: true,
    forbidNonWhitelisted: true,
  }));

  // API versioning
  app.enableVersioning({
    type: VersioningType.URI,
    defaultVersion: '1',
  });

  // Swagger configuration
  const config = new DocumentBuilder()
    .setTitle('Product Service API')
    .setDescription('REST API for product management')
    .setVersion('1.0')
    .addTag('Products')
    .addBearerAuth()
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  // Export OpenAPI JSON for API gateway
  writeFileSync('./openapi.json', JSON.stringify(document, null, 2));

  await app.listen(process.env.PORT ?? 3000, '0.0.0.0');
}
bootstrap();
```
