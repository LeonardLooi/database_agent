## Response Format Options

Support multiple output formats for flexibility:

```typescript
enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json"
}

const inputSchema = z.object({
  query: z.string(),
  response_format: z.nativeEnum(ResponseFormat)
    .default(ResponseFormat.MARKDOWN)
    .describe("Output format: 'markdown' for human-readable or 'json' for machine-readable")
});
```

**Markdown format**: Use headers, lists, formatting. Convert timestamps to human-readable format. Show display names with IDs in parentheses. Omit verbose metadata.

**JSON format**: Return complete, structured data suitable for programmatic processing. Include all available fields and metadata. Use consistent field names and types.

## Pagination Implementation

```typescript
const ListSchema = z.object({
  limit: z.number().int().min(1).max(100).default(20),
  offset: z.number().int().min(0).default(0)
});

async function listItems(params: z.infer<typeof ListSchema>) {
  const data = await apiRequest(params.limit, params.offset);
  const response = {
    total: data.total,
    count: data.items.length,
    offset: params.offset,
    items: data.items,
    has_more: data.total > params.offset + data.items.length,
    next_offset: data.total > params.offset + data.items.length
      ? params.offset + data.items.length : undefined
  };
  return JSON.stringify(response, null, 2);
}
```

## Character Limits and Truncation

Add a CHARACTER_LIMIT constant to prevent overwhelming responses:

```typescript
export const CHARACTER_LIMIT = 25000;

async function searchTool(params: SearchInput) {
  let result = generateResponse(data);
  if (result.length > CHARACTER_LIMIT) {
    const truncatedData = data.slice(0, Math.max(1, data.length / 2));
    response.data = truncatedData;
    response.truncated = true;
    response.truncation_message =
      `Response truncated from ${data.length} to ${truncatedData.length} items. ` +
      `Use 'offset' parameter or add filters to see more results.`;
    result = JSON.stringify(response, null, 2);
  }
  return result;
}
```

## Error Handling

Provide clear, actionable error messages:

```typescript
import axios, { AxiosError } from "axios";

function handleApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response) {
      switch (error.response.status) {
        case 404: return "Error: Resource not found. Please check the ID is correct.";
        case 403: return "Error: Permission denied. You don't have access to this resource.";
        case 429: return "Error: Rate limit exceeded. Please wait before making more requests.";
        default: return `Error: API request failed with status ${error.response.status}`;
      }
    } else if (error.code === "ECONNABORTED") {
      return "Error: Request timed out. Please try again.";
    }
  }
  return `Error: Unexpected error occurred: ${error instanceof Error ? error.message : String(error)}`;
}
```

## Shared Utilities

Extract common functionality into reusable functions:

```typescript
async function makeApiRequest<T>(
  endpoint: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
  data?: any,
  params?: any
): Promise<T> {
  const response = await axios({
    method,
    url: `${API_BASE_URL}/${endpoint}`,
    data, params,
    timeout: 30000,
    headers: { "Content-Type": "application/json", "Accept": "application/json" }
  });
  return response.data;
}
```

## TypeScript Best Practices

1. **Use Strict TypeScript**: Enable strict mode in tsconfig.json
2. **Define Interfaces**: Create clear interface definitions for all data structures
3. **Avoid `any`**: Use proper types or `unknown` instead of `any`
4. **Zod for Runtime Validation**: Use Zod schemas to validate external data
5. **Type Guards**: Create type guard functions for complex type checking
6. **Error Handling**: Always use try-catch with proper error type checking
7. **Null Safety**: Use optional chaining (`?.`) and nullish coalescing (`??`)

```typescript
interface UserResponse {
  id: string;
  name: string;
  email: string;
  team?: string;
  active: boolean;
}

const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  team: z.string().optional(),
  active: z.boolean()
});

type User = z.infer<typeof UserSchema>;

async function getUser(id: string): Promise<User> {
  const data = await apiCall(`/users/${id}`);
  return UserSchema.parse(data);  // Runtime validation
}
```

## Code Composability

Your implementation MUST prioritize composability and code reuse:

1. **Extract Common Functionality**: Create reusable helpers for operations used across multiple tools. Build shared API clients. Centralize error handling logic.
2. **Avoid Duplication**: NEVER copy-paste similar code between tools. If similar logic appears twice, extract it into a function. Common operations like pagination, filtering, and formatting should be shared.
