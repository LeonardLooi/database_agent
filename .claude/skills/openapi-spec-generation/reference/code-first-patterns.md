# Code-First OpenAPI Patterns

Generate OpenAPI specs directly from annotated code. Each stack auto-generates the spec from type hints, decorators, or annotations.

## Quick Reference

| Language | Tool | Annotation Style | Output |
|----------|------|------------------|--------|
| **Python** | FastAPI + Pydantic | Type hints + `Field()` | Auto at `/openapi.json` |
| **Java/Kotlin** | springdoc-openapi | `@Operation`, `@Schema` | Auto at `/v3/api-docs` |
| **TypeScript** | tsoa | Decorators (`@Get`, `@Response`) | Generated at build time |

## Extraction Commands

| Stack | Command |
|-------|---------|
| FastAPI | `python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json` |
| Spring Boot | `curl http://localhost:8080/v3/api-docs > openapi.json` |
| tsoa | `npx tsoa spec` |

---

## Java / Spring Boot (springdoc-openapi)

### Dependency

```java
// build.gradle.kts
dependencies {
    implementation("org.springdoc:springdoc-openapi-starter-webflux-ui:2.8.0")
}
```

### Configuration

```yaml
# application.yml
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
    tags-sorter: alpha
    operations-sorter: alpha
```

### OpenAPI Config Bean

```java
// OpenApiConfig.java
@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("User Management API")
                .version("2.0.0")
                .description("API for managing users and profiles")
                .contact(new Contact()
                    .name("API Support")
                    .email("api-support@example.com")))
            .addSecurityItem(new SecurityRequirement().addList("bearerAuth"))
            .components(new Components()
                .addSecuritySchemes("bearerAuth", new SecurityScheme()
                    .type(SecurityScheme.Type.HTTP)
                    .scheme("bearer")
                    .bearerFormat("JWT")));
    }
}
```

### Annotated Controller

```java
// UserController.java
@RestController
@RequestMapping("/api/v1/users")
@Tag(name = "Users", description = "User management operations")
@SecurityRequirement(name = "bearerAuth")
public class UserController {

    @Operation(
        summary = "List all users",
        description = "Returns paginated list with optional filtering"
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Success",
            content = @Content(schema = @Schema(implementation = UserListResponse.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized")
    })
    @GetMapping
    public Mono<UserListResponse> listUsers(
        @Parameter(description = "Page number (1-based)")
        @RequestParam(defaultValue = "1") @Min(1) int page,

        @Parameter(description = "Items per page")
        @RequestParam(defaultValue = "20") @Min(1) @Max(100) int limit,

        @Parameter(description = "Filter by status")
        @RequestParam(required = false) UserStatus status,

        @Parameter(description = "Search by name or email")
        @RequestParam(required = false) @Size(min = 2, max = 100) String search
    ) {
        // Implementation
    }

    @Operation(summary = "Create a new user")
    @ApiResponses({
        @ApiResponse(responseCode = "201", description = "User created",
            content = @Content(schema = @Schema(implementation = User.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request"),
        @ApiResponse(responseCode = "409", description = "Email already exists")
    })
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<User> createUser(
        @Valid @RequestBody CreateUserRequest request
    ) {
        // Implementation
    }

    @Operation(summary = "Get user by ID")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Success"),
        @ApiResponse(responseCode = "404", description = "User not found")
    })
    @GetMapping("/{userId}")
    public Mono<User> getUser(
        @Parameter(description = "User ID", required = true)
        @PathVariable UUID userId
    ) {
        // Implementation
    }

    @Operation(summary = "Update user")
    @PatchMapping("/{userId}")
    public Mono<User> updateUser(
        @PathVariable UUID userId,
        @Valid @RequestBody UpdateUserRequest request
    ) {
        // Implementation
    }

    @Operation(summary = "Delete user")
    @DeleteMapping("/{userId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Tag(name = "Admin")
    public Mono<Void> deleteUser(@PathVariable UUID userId) {
        // Implementation
    }
}
```

### DTOs with Schema Annotations

```java
// DTOs with schema annotations
@Schema(description = "User entity")
public record User(
    @Schema(description = "Unique identifier", format = "uuid")
    UUID id,

    @Schema(description = "Email address", format = "email")
    String email,

    @Schema(description = "Display name", minLength = 1, maxLength = 100)
    String name,

    @Schema(description = "Account status")
    UserStatus status,

    @Schema(description = "User role", defaultValue = "user")
    UserRole role,

    @Schema(description = "Created timestamp")
    Instant createdAt
) {}

@Schema(description = "Create user request")
public record CreateUserRequest(
    @Schema(description = "Email address", format = "email", requiredMode = REQUIRED)
    @NotBlank @Email String email,

    @Schema(description = "Display name", minLength = 1, maxLength = 100, requiredMode = REQUIRED)
    @NotBlank @Size(min = 1, max = 100) String name,

    @Schema(description = "User role", defaultValue = "user")
    UserRole role
) {}
```

---

## Python / FastAPI

```python
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

app = FastAPI(
    title="User Management API",
    description="API for managing users and profiles",
    version="2.0.0",
    openapi_tags=[
        {"name": "Users", "description": "User operations"},
        {"name": "Admin", "description": "Admin operations"},
    ],
    servers=[
        {"url": "https://api.example.com/v2", "description": "Production"},
        {"url": "http://localhost:8000", "description": "Development"},
    ],
)

# Enums
class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"

class UserRole(str, Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"

# Models
class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    role: UserRole = Field(default=UserRole.user)

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "user@example.com", "name": "John Doe", "role": "user"}]
        }
    }

class User(BaseModel):
    id: UUID = Field(..., description="Unique identifier")
    email: EmailStr
    name: str
    status: UserStatus
    role: UserRole
    created_at: datetime = Field(..., alias="createdAt")

    model_config = {"populate_by_name": True}

class UserListResponse(BaseModel):
    data: List[User]
    pagination: dict

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")

# Endpoints
@app.get("/users", response_model=UserListResponse, tags=["Users"])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
):
    """List users with pagination and filtering."""
    pass

@app.post("/users", response_model=User, status_code=201, tags=["Users"],
          responses={409: {"model": ErrorResponse, "description": "Email exists"}})
async def create_user(user: UserCreate):
    """Create a new user and send welcome email."""
    pass

@app.get("/users/{user_id}", response_model=User, tags=["Users"],
         responses={404: {"model": ErrorResponse}})
async def get_user(user_id: UUID = Path(..., description="User ID")):
    """Get user by ID."""
    pass

@app.delete("/users/{user_id}", status_code=204, tags=["Users", "Admin"])
async def delete_user(user_id: UUID = Path(..., description="User ID")):
    """Delete user permanently."""
    pass

# Export: python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))"
```

---

## TypeScript / tsoa

```typescript
import {
  Controller, Get, Post, Patch, Delete, Route, Path, Query, Body,
  Response, SuccessResponse, Tags, Security, Example,
} from "tsoa";

interface User {
  id: string;
  email: string;
  name: string;
  status: "active" | "inactive" | "suspended";
  role: "user" | "moderator" | "admin";
  createdAt: Date;
}

interface CreateUserRequest {
  email: string;
  name: string;
  role?: "user" | "moderator" | "admin";
}

interface ErrorResponse {
  code: string;
  message: string;
}

@Route("users")
@Tags("Users")
export class UsersController extends Controller {

  @Get()
  @Security("bearerAuth")
  @Response<ErrorResponse>(401, "Unauthorized")
  public async listUsers(
    @Query() page: number = 1,
    @Query() limit: number = 20,
    @Query() status?: string,
  ): Promise<{ data: User[]; pagination: object }> {
    throw new Error("Not implemented");
  }

  @Post()
  @Security("bearerAuth")
  @SuccessResponse(201, "Created")
  @Response<ErrorResponse>(400, "Invalid request")
  @Response<ErrorResponse>(409, "Email exists")
  public async createUser(@Body() body: CreateUserRequest): Promise<User> {
    this.setStatus(201);
    throw new Error("Not implemented");
  }

  @Get("{userId}")
  @Security("bearerAuth")
  @Response<ErrorResponse>(404, "Not found")
  public async getUser(@Path() userId: string): Promise<User> {
    throw new Error("Not implemented");
  }

  @Delete("{userId}")
  @Tags("Users", "Admin")
  @Security("bearerAuth")
  @SuccessResponse(204, "Deleted")
  public async deleteUser(@Path() userId: string): Promise<void> {
    this.setStatus(204);
  }
}
```
