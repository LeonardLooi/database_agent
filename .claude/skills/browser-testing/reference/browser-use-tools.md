# Browser-Use MCP — Tool Reference

## When to Use Browser-Use MCP

Use browser-use when the task involves acting like a human user:

- Filling out forms step by step
- Multi-step user flows (signup → verify → dashboard)
- Testing UI interactions (click, type, select, scroll)
- Running parallel browser sessions
- Using real Chrome with existing logins (`--browser real`)
- Element-by-index interaction for precise control

## Core Workflow

The typical browser-use workflow:

1. **Navigate** to target URL
2. **Get state** to see all interactive elements with indices
3. **Interact** using indices (click, type, select)
4. **Verify** state changed as expected
5. **Repeat** for multi-step flows

## Navigation & Session Management

### browser_navigate
Navigate to a URL in the current or new tab.

```typescript
browser_navigate({
  url: "https://example.com/login",
  new_tab: false  // true = open in new tab
})
```

**Returns:** Confirmation with final URL (handles redirects).

### browser_list_sessions
List all active browser sessions.

```typescript
browser_list_sessions()
```

### browser_list_tabs
List all tabs in the current session.

```typescript
browser_list_tabs()
```

### browser_switch_tab
Switch to a different tab by index.

```typescript
browser_switch_tab({ index: 0 })
```

### browser_close_tab
Close a specific tab.

```typescript
browser_close_tab({ index: 1 })
```

### browser_close_session
Close a specific browser session.

```typescript
browser_close_session({ session_id: "abc123" })
```

### browser_close_all
Close all browser sessions.

```typescript
browser_close_all()
```

**IMPORTANT:** Always close sessions when done to free resources.

## State Inspection

### browser_get_state
Get current page state with all interactive elements and their indices.

```typescript
browser_get_state({
  include_screenshot: false  // NEVER set to true unless explicitly asked
})
```

**Returns:**
```json
{
  "url": "https://example.com/login",
  "title": "Login Page",
  "tabs": [...],
  "interactive_elements": [
    { "index": 4, "tag": "input", "text": "", "type": "text" },
    { "index": 5, "tag": "input", "text": "", "type": "password" },
    { "index": 6, "tag": "button", "text": "Login" }
  ]
}
```

**CRITICAL RULE:** `include_screenshot: false` by default. Screenshots generate 126K+ characters and cause token overflow. Only use screenshots when user explicitly requests visual confirmation.

**Elements include:**
- `index` — Used for all interactions
- `tag` — HTML element type (input, button, a, select, etc.)
- `text` — Visible text content
- `type` — Input type (text, password, email, etc.) if applicable
- `href` — Link destination if applicable
- `value` — Current value if applicable

## User Interactions

### browser_click
Click an element by its index.

```typescript
browser_click({
  index: 6,
  new_tab: false  // true = open links in new tab
})
```

**Use for:**
- Buttons
- Links
- Checkboxes/radio buttons
- Any clickable element

### browser_type
Type text into the currently focused element.

```typescript
browser_type({
  index: 4,
  text: "user@example.com"
})
```

**Note:** Element must be focused first (click on it or use browser_input).

### browser_input
Click an element then type text (combines click + type).

```typescript
browser_input({
  index: 4,
  text: "user@example.com"
})
```

**Use for:** Form filling — more reliable than click + type separately.

### browser_select
Select an option from a dropdown by value or text.

```typescript
browser_select({
  index: 8,
  value: "option2"
})
```

### browser_scroll
Scroll the page up or down.

```typescript
browser_scroll({ direction: "down", amount: 500 })
browser_scroll({ direction: "up", amount: 300 })
```

**Parameters:**
- `direction`: "up" or "down"
- `amount`: Pixels to scroll (default: 300)

### browser_keys
Send keyboard shortcuts or special keys.

```typescript
browser_keys({ keys: "Enter" })
browser_keys({ keys: "Tab" })
browser_keys({ keys: "Escape" })
browser_keys({ keys: "Control+A" })
browser_keys({ keys: "Command+V" })  // macOS
```

**Common keys:**
- Enter, Tab, Escape, Backspace, Delete
- ArrowUp, ArrowDown, ArrowLeft, ArrowRight
- Control+C, Control+V (Windows/Linux)
- Command+C, Command+V (macOS)

## Advanced Features

### Using Real Chrome with Existing Sessions

Launch browser-use with your local Chrome to test with real logins:

```bash
browser-use --browser real
```

**Benefits:**
- Use existing logged-in sessions (Google, GitHub, etc.)
- Test with real cookies and auth state
- Access local development servers
- Bypass CAPTCHAs that trust your browser

**Limitations:**
- Cannot run in headless mode
- May interfere with manual browsing
- Slower than headless mode

### Parallel Browser Sessions

Browser-use supports multiple concurrent sessions:

```typescript
// Session 1: Test user flow A
browser_navigate({ url: "https://app.com/signup" })
// ... interact ...

// Session 2: Test user flow B (new session created automatically)
browser_navigate({ url: "https://app.com/login", new_tab: true })
// ... interact ...

// List all sessions
browser_list_sessions()

// Close specific session
browser_close_session({ session_id: "session_1" })
```

## Best Practices

### 1. Always Get State Before Interacting

```typescript
// ❌ BAD - Guessing element index
browser_click({ index: 5 })

// ✅ GOOD - Get state first to see what index 5 actually is
const state = browser_get_state({ include_screenshot: false })
// Verify index 5 is the submit button
browser_click({ index: 5 })
```

### 2. Use browser_input for Form Fields

```typescript
// ❌ BAD - Unreliable
browser_click({ index: 4 })
browser_type({ index: 4, text: "email@example.com" })

// ✅ GOOD - More reliable
browser_input({ index: 4, text: "email@example.com" })
```

### 3. Verify State Changes

```typescript
// Fill form and submit
browser_input({ index: 4, text: "user@example.com" })
browser_input({ index: 5, text: "password123" })
browser_click({ index: 6 })

// ✅ Verify navigation happened
const newState = browser_get_state({ include_screenshot: false })
// Check if URL changed to /dashboard
```

### 4. Close Sessions When Done

```typescript
// ✅ Always clean up
browser_close_all()
```

### 5. Handle Multi-Page Flows

```typescript
// Step 1: Login
browser_navigate({ url: "https://app.com/login" })
browser_get_state({ include_screenshot: false })
browser_input({ index: 4, text: "user@example.com" })
browser_input({ index: 5, text: "password123" })
browser_click({ index: 6 })

// Step 2: Verify redirect to dashboard
const state = browser_get_state({ include_screenshot: false })
// Assert URL contains "/dashboard"

// Step 3: Navigate to settings
browser_click({ index: 10 })  // Settings link

// Step 4: Update profile
browser_get_state({ include_screenshot: false })
browser_input({ index: 15, text: "New Name" })
browser_click({ index: 20 })  // Save button
```

### 6. Handle Dynamic Content

```typescript
// Wait for content to load by checking state
browser_get_state({ include_screenshot: false })
// If expected element not present, wait and retry
browser_scroll({ direction: "down", amount: 300 })
browser_get_state({ include_screenshot: false })
```

### 7. Debugging Failed Interactions

When an interaction doesn't work:

1. Get fresh state to see current elements
2. Verify element index is correct
3. Check if page loaded completely
4. Try scrolling to element first
5. As last resort, request screenshot: `browser_get_state({ include_screenshot: true })`

## Common Patterns

### Login Flow
```typescript
browser_navigate({ url: "https://app.com/login" })
const state = browser_get_state({ include_screenshot: false })
// Find username and password inputs by examining state
browser_input({ index: 4, text: "user@example.com" })
browser_input({ index: 5, text: "password123" })
browser_click({ index: 6 })  // Submit button
const result = browser_get_state({ include_screenshot: false })
// Verify URL changed to /dashboard
```

### Form Submission
```typescript
browser_navigate({ url: "https://app.com/contact" })
browser_get_state({ include_screenshot: false })
browser_input({ index: 5, text: "John Doe" })
browser_input({ index: 6, text: "john@example.com" })
browser_input({ index: 7, text: "Hello, I need help with..." })
browser_select({ index: 8, value: "support" })
browser_click({ index: 9 })  // Submit
browser_get_state({ include_screenshot: false })
// Verify success message appeared
```

### Multi-Step Wizard
```typescript
// Step 1
browser_navigate({ url: "https://app.com/signup" })
browser_get_state({ include_screenshot: false })
browser_input({ index: 4, text: "user@example.com" })
browser_click({ index: 5 })  // Next button

// Step 2
browser_get_state({ include_screenshot: false })
browser_input({ index: 6, text: "John Doe" })
browser_input({ index: 7, text: "Company Inc" })
browser_click({ index: 8 })  // Next button

// Step 3
browser_get_state({ include_screenshot: false })
browser_click({ index: 10 })  // Finish button

// Verify completion
const final = browser_get_state({ include_screenshot: false })
// Check URL is /welcome or success message present
```

## Error Handling

### Session Closed Unexpectedly
If session closes (crash, timeout), create new session:
```typescript
try {
  browser_click({ index: 5 })
} catch (error) {
  // Session may have crashed
  browser_close_all()
  browser_navigate({ url: startUrl })
}
```

### Element Not Found
Get fresh state if element index is invalid:
```typescript
// Element 15 not found
const state = browser_get_state({ include_screenshot: false })
// Re-examine interactive_elements array
// Element indices may have changed due to dynamic content
```

### Navigation Timeout
Increase wait time or check if page is blocking:
```typescript
// If navigation hangs, check for dialogs/popups
browser_get_state({ include_screenshot: false })
// Look for modal dialogs that need to be closed
```

### Token Overflow from Screenshot
Never use `include_screenshot: true` unless explicitly requested:
```typescript
// ❌ FORBIDDEN (unless user asks for visual)
browser_get_state({ include_screenshot: true })

// ✅ DEFAULT
browser_get_state({ include_screenshot: false })
```
