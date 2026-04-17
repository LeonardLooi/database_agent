# OpenAPI Skeleton Template

Minimal copy-paste starter for OpenAPI 3.1 specifications. Use this as the foundation for any new API spec.

## OpenAPI 3.1 Structure Overview

```yaml
openapi: 3.1.0
info:
  title: API Title
  version: 1.0.0
servers:
  - url: https://api.example.com/v1
paths:
  /resources:
    get: ...
components:
  schemas: ...
  securitySchemes: ...
```

## Design Approaches

| Approach | Description | Best For |
|----------|-------------|----------|
| **Design-First** | Write spec before code | New APIs, contracts, external consumers |
| **Code-First** | Generate spec from code | Existing APIs, rapid iteration |
| **Hybrid** | Annotate code, generate spec | Evolving APIs, keep spec in sync |

## Minimal Skeleton (Copy-Paste Starter)

```yaml
openapi: 3.1.0
info:
  title: My API
  version: 1.0.0
  description: API description here

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: http://localhost:8080/v1
    description: Local

paths:
  /resources:
    get:
      operationId: listResources
      summary: List resources
      tags: [Resources]
      parameters:
        - $ref: "#/components/parameters/PageParam"
        - $ref: "#/components/parameters/LimitParam"
      responses:
        "200":
          description: Success
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ResourceList"
        "401":
          $ref: "#/components/responses/Unauthorized"
      security:
        - bearerAuth: []

    post:
      operationId: createResource
      summary: Create resource
      tags: [Resources]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateResourceRequest"
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Resource"
        "400":
          $ref: "#/components/responses/BadRequest"
      security:
        - bearerAuth: []

components:
  schemas:
    Resource:
      type: object
      required: [id, name, createdAt]
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        createdAt:
          type: string
          format: date-time

    CreateResourceRequest:
      type: object
      required: [name]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100

    ResourceList:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: "#/components/schemas/Resource"
        pagination:
          $ref: "#/components/schemas/Pagination"

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer

    Error:
      type: object
      required: [code, message]
      properties:
        code:
          type: string
        message:
          type: string

  parameters:
    PageParam:
      name: page
      in: query
      schema:
        type: integer
        default: 1
        minimum: 1

    LimitParam:
      name: limit
      in: query
      schema:
        type: integer
        default: 20
        minimum: 1
        maximum: 100

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Error"

    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Error"

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

## Customization Checklist

After copying the skeleton, update these fields:

1. `info.title` -- Set the actual API name
2. `info.version` -- Set the initial version
3. `info.description` -- Describe the API purpose
4. `servers` -- Add production, staging, and local URLs
5. `paths` -- Replace `/resources` with actual endpoint paths
6. `components.schemas` -- Replace `Resource` with actual domain models
7. `securitySchemes` -- Adjust auth mechanism (JWT, API key, OAuth2)
