# NestJS REST Controllers — DTOs, Mapping & Pagination

DTO mapping patterns, pagination, filtering, and sorting for NestJS 11.x REST APIs with Prisma ORM and TypeScript 5.x.

## 3. DTO Mapping Patterns

### Pattern 1: Static Factory Methods

```typescript
import { ApiProperty } from '@nestjs/swagger';
import { Product } from '@prisma/client';

export class ProductResponseDto {
  @ApiProperty({ example: '123e4567-e89b-12d3-a456-426614174000' })
  id: string;

  @ApiProperty({ example: 'Wireless Mouse' })
  name: string;

  @ApiProperty({ example: 'MOUSE-001' })
  sku: string;

  @ApiProperty({ example: 29.99 })
  price: number;

  @ApiProperty({ enum: ['ACTIVE', 'INACTIVE', 'ARCHIVED'] })
  status: string;

  @ApiProperty()
  createdAt: Date;

  @ApiProperty()
  updatedAt: Date;

  // Static factory method for single entity
  static fromEntity(entity: Product): ProductResponseDto {
    const dto = new ProductResponseDto();
    dto.id = entity.id;
    dto.name = entity.name;
    dto.sku = entity.sku;
    dto.price = entity.price.toNumber(); // Prisma Decimal → number
    dto.status = entity.status;
    dto.createdAt = entity.createdAt;
    dto.updatedAt = entity.updatedAt;
    return dto;
  }

  // Static factory method for entity list
  static fromEntityList(entities: Product[]): ProductResponseDto[] {
    return entities.map(entity => this.fromEntity(entity));
  }
}
```

### Pattern 2: class-transformer with @Expose/@Exclude

```typescript
import { Expose, Exclude, plainToInstance } from 'class-transformer';
import { ApiProperty } from '@nestjs/swagger';
import { Product } from '@prisma/client';

@Exclude()
export class ProductResponseDto {
  @Expose()
  @ApiProperty()
  id: string;

  @Expose()
  @ApiProperty()
  name: string;

  @Expose()
  @ApiProperty()
  sku: string;

  @Expose()
  @ApiProperty()
  price: number;

  @Expose()
  @ApiProperty()
  status: string;

  @Expose()
  @ApiProperty()
  createdAt: Date;

  @Expose()
  @ApiProperty()
  updatedAt: Date;

  // Factory using plainToInstance
  static fromEntity(entity: Product): ProductResponseDto {
    return plainToInstance(ProductResponseDto, entity, {
      excludeExtraneousValues: true,
    });
  }
}
```

### Pattern 3: Dedicated Mapper Service

```typescript
import { Injectable } from '@nestjs/common';
import { Prisma, Product } from '@prisma/client';
import { CreateProductDto, UpdateProductDto, ProductResponseDto } from './dto';

@Injectable()
export class ProductMapper {
  toResponse(entity: Product): ProductResponseDto {
    return {
      id: entity.id,
      name: entity.name,
      sku: entity.sku,
      price: entity.price.toNumber(),
      status: entity.status,
      createdAt: entity.createdAt,
      updatedAt: entity.updatedAt,
    };
  }

  toResponseList(entities: Product[]): ProductResponseDto[] {
    return entities.map(e => this.toResponse(e));
  }

  toCreateInput(dto: CreateProductDto): Prisma.ProductCreateInput {
    return {
      name: dto.name,
      sku: dto.sku,
      price: new Prisma.Decimal(dto.price),
      status: dto.status ?? 'ACTIVE',
      description: dto.description,
    };
  }

  toUpdateInput(dto: UpdateProductDto): Prisma.ProductUpdateInput {
    const data: Prisma.ProductUpdateInput = {};
    if (dto.name !== undefined) data.name = dto.name;
    if (dto.price !== undefined) data.price = new Prisma.Decimal(dto.price);
    if (dto.status !== undefined) data.status = dto.status;
    if (dto.description !== undefined) data.description = dto.description;
    return data;
  }
}
```

---

## 4. Pagination, Filtering & Sorting

### Generic Pagination DTO

```typescript
import { IsOptional, IsInt, Min, Max, IsString, IsEnum } from 'class-validator';
import { Type } from 'class-transformer';
import { ApiPropertyOptional } from '@nestjs/swagger';

export enum SortOrder {
  ASC = 'asc',
  DESC = 'desc',
}

export class PaginationQueryDto {
  @ApiPropertyOptional({ minimum: 1, default: 1 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  page: number = 1;

  @ApiPropertyOptional({ minimum: 1, maximum: 100, default: 20 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit: number = 20;

  @ApiPropertyOptional({ default: 'createdAt' })
  @IsOptional()
  @IsString()
  sortBy: string = 'createdAt';

  @ApiPropertyOptional({ enum: SortOrder, default: SortOrder.DESC })
  @IsOptional()
  @IsEnum(SortOrder)
  sortOrder: SortOrder = SortOrder.DESC;

  get skip(): number {
    return (this.page - 1) * this.limit;
  }

  get take(): number {
    return this.limit;
  }
}
```

### Generic Paginated Response

```typescript
import { ApiProperty } from '@nestjs/swagger';

export class PaginationMeta {
  @ApiProperty()
  page: number;

  @ApiProperty()
  limit: number;

  @ApiProperty()
  total: number;

  @ApiProperty()
  totalPages: number;

  @ApiProperty()
  hasNextPage: boolean;

  @ApiProperty()
  hasPreviousPage: boolean;
}

export class PaginatedResponse<T> {
  @ApiProperty({ isArray: true })
  data: T[];

  @ApiProperty({ type: PaginationMeta })
  meta: PaginationMeta;

  static create<T>(
    data: T[],
    total: number,
    page: number,
    limit: number,
  ): PaginatedResponse<T> {
    const totalPages = Math.ceil(total / limit);
    return {
      data,
      meta: {
        page,
        limit,
        total,
        totalPages,
        hasNextPage: page < totalPages,
        hasPreviousPage: page > 1,
      },
    };
  }
}
```

### Product Filter DTO

```typescript
import { IsOptional, IsString, IsEnum, IsNumber, Min } from 'class-validator';
import { Type } from 'class-transformer';
import { ApiPropertyOptional } from '@nestjs/swagger';
import { PaginationQueryDto } from '@/common/dto/pagination-query.dto';

export enum ProductStatus {
  ACTIVE = 'ACTIVE',
  INACTIVE = 'INACTIVE',
  ARCHIVED = 'ARCHIVED',
}

export class ProductFilterDto extends PaginationQueryDto {
  @ApiPropertyOptional({ description: 'Search in name, SKU, or description' })
  @IsOptional()
  @IsString()
  search?: string;

  @ApiPropertyOptional({ enum: ProductStatus })
  @IsOptional()
  @IsEnum(ProductStatus)
  status?: ProductStatus;

  @ApiPropertyOptional({ minimum: 0 })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(0)
  minPrice?: number;

  @ApiPropertyOptional({ minimum: 0 })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(0)
  maxPrice?: number;
}
```

### Repository with Pagination Implementation

```typescript
import { Injectable } from '@nestjs/common';
import { PrismaService } from '@/core/prisma/prisma.service';
import { Prisma, Product } from '@prisma/client';
import { ProductFilterDto } from './dto';

@Injectable()
export class ProductRepository {
  constructor(private readonly prisma: PrismaService) {}

  async findManyWithPagination(filter: ProductFilterDto): Promise<[Product[], number]> {
    const where = this.buildWhereClause(filter);
    const orderBy = { [filter.sortBy]: filter.sortOrder };

    const [data, total] = await Promise.all([
      this.prisma.product.findMany({
        where,
        orderBy,
        skip: filter.skip,
        take: filter.take,
      }),
      this.prisma.product.count({ where }),
    ]);

    return [data, total];
  }

  private buildWhereClause(filter: ProductFilterDto): Prisma.ProductWhereInput {
    const where: Prisma.ProductWhereInput = {};

    if (filter.search) {
      where.OR = [
        { name: { contains: filter.search, mode: 'insensitive' } },
        { sku: { contains: filter.search, mode: 'insensitive' } },
        { description: { contains: filter.search, mode: 'insensitive' } },
      ];
    }

    if (filter.status) {
      where.status = filter.status;
    }

    if (filter.minPrice !== undefined || filter.maxPrice !== undefined) {
      where.price = {};
      if (filter.minPrice !== undefined) {
        where.price.gte = new Prisma.Decimal(filter.minPrice);
      }
      if (filter.maxPrice !== undefined) {
        where.price.lte = new Prisma.Decimal(filter.maxPrice);
      }
    }

    return where;
  }
}
```
