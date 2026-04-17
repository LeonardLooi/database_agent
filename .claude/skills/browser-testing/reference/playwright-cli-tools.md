# playwright-cli — Tool Reference

`playwright-cli` is the stateful Bash CLI for browser automation in Claude Code. The npm package is `@playwright/mcp`; the installed binary is `playwright-cli`. All commands are invoked via `Bash`.

## Install

```bash
npm install -g @playwright/mcp@latest
playwright-cli install       # download browsers
playwright-cli --version     # verify
```

## Session Model

playwright-cli is **stateful** — a named session keeps the browser open between commands. Use `-s=<name>` to target a session:

```bash
playwright-cli -s=my-session <command>
```

Without `-s`, commands use a shared default session.

---

## Navigation

### goto
Navigate to a URL.
```bash
playwright-cli -s=test goto http://localhost:4200/login
playwright-cli goto https://example.com
```

### open
Open the browser (optionally at a URL). Use for the initial launch.
```bash
playwright-cli open
playwright-cli open http://localhost:4200
```

### reload
Reload the current page.
```bash
playwright-cli -s=test reload
```

### go-back / go-forward
```bash
playwright-cli -s=test go-back
playwright-cli -s=test go-forward
```

---

## Snapshot (Accessibility Tree)

Get the accessibility tree to discover element refs. **Always run before click/fill** — refs change between renders.

```bash
playwright-cli -s=test snapshot
```

Returns a structured tree. Each interactive element has a `[ref]` identifier like `[button-submit-3]` or `[input-email-1]`. Use these refs in subsequent commands.

---

## Interaction

### fill
Fill a text input by ref (sets value directly — no keystroke simulation).
```bash
playwright-cli -s=test fill [input-email-1] "user@example.com"
playwright-cli -s=test fill [input-password-2] "secret123"
```

### type
Type text character-by-character into the focused element (simulates keystrokes — use for autocomplete triggers).
```bash
playwright-cli -s=test type "Hello World"
```

### click
Click an element by ref.
```bash
playwright-cli -s=test click [button-submit-3]
```

### dblclick
Double-click an element.
```bash
playwright-cli -s=test dblclick [element-ref]
```

### hover
Move mouse over an element (triggers hover states, tooltips).
```bash
playwright-cli -s=test hover [button-menu-4]
```

### select
Select an option in a dropdown.
```bash
playwright-cli -s=test select [select-country-2] "AU"
```

### check / uncheck
Check or uncheck a checkbox or radio button.
```bash
playwright-cli -s=test check [checkbox-terms-5]
playwright-cli -s=test uncheck [checkbox-newsletter-6]
```

### drag
Drag from one element to another.
```bash
playwright-cli -s=test drag [source-ref] [target-ref]
```

### upload
Upload a file via a file input.
```bash
playwright-cli -s=test upload /tmp/test-document.pdf
```

---

## Keyboard

### press
Press a key or shortcut.
```bash
playwright-cli -s=test press Enter
playwright-cli -s=test press Tab
playwright-cli -s=test press Escape
playwright-cli -s=test press "Control+a"
playwright-cli -s=test press "ArrowDown"
```

### keydown / keyup
Hold a key down or release it (for modifier key sequences).
```bash
playwright-cli -s=test keydown Shift
playwright-cli -s=test keyup Shift
```

---

## Mouse

```bash
playwright-cli -s=test mousemove 400 300     # move to coordinates
playwright-cli -s=test mousedown             # press left button
playwright-cli -s=test mouseup               # release
playwright-cli -s=test mousewheel 0 -300     # scroll up
```

---

## Inspection

### network
List all network requests since the page loaded.
```bash
playwright-cli -s=test network
```
Returns: method, URL, status, timing for each request. **Run after form submissions and navigations.**

### console
List console messages.
```bash
playwright-cli -s=test console          # all messages
playwright-cli -s=test console error    # errors only
playwright-cli -s=test console warn     # warnings only
```
**Rule:** Any `error` message = automatic NEEDS WORK in validation reviews.

### eval
Execute JavaScript in the page context.
```bash
playwright-cli -s=test eval "localStorage.getItem('authToken')"
playwright-cli -s=test eval "document.title"
playwright-cli -s=test eval "JSON.parse(localStorage.getItem('user') || '{}')"
```

---

## Visual

### screenshot
Capture a screenshot of the current page or a specific element.
```bash
playwright-cli -s=test screenshot                          # inline base64
playwright-cli -s=test screenshot --output baseline.png   # save to file
playwright-cli -s=test screenshot [element-ref]            # element only
```

### pdf
Save the current page as a PDF.
```bash
playwright-cli -s=test pdf --output page.pdf
```

---

## Page Control

### resize
Set the browser viewport dimensions.
```bash
playwright-cli -s=test resize 375 812    # iPhone 14
playwright-cli -s=test resize 768 1024   # iPad
playwright-cli -s=test resize 1280 720   # Desktop
```

### dialog-accept / dialog-dismiss
Handle browser dialogs (alert, confirm, prompt). Set BEFORE the action that triggers the dialog.
```bash
playwright-cli -s=test dialog-accept
playwright-cli -s=test dialog-accept "my prompt text"
playwright-cli -s=test dialog-dismiss
```

---

## Tabs

```bash
playwright-cli -s=test tab-list                             # list open tabs
playwright-cli -s=test tab-new http://localhost:4200/admin  # open new tab
playwright-cli -s=test tab-select 1                         # switch to tab by index
playwright-cli -s=test tab-close 1                          # close tab by index
```

---

## Storage

### localStorage
```bash
playwright-cli -s=test localstorage-list
playwright-cli -s=test localstorage-get authToken
playwright-cli -s=test localstorage-set theme dark
playwright-cli -s=test localstorage-delete authToken
playwright-cli -s=test localstorage-clear
```

### sessionStorage
```bash
playwright-cli -s=test sessionstorage-list
playwright-cli -s=test sessionstorage-get sessionId
```

### Cookies
```bash
playwright-cli -s=test cookie-list
playwright-cli -s=test cookie-get sessionToken
playwright-cli -s=test cookie-set myKey myValue
playwright-cli -s=test cookie-delete myKey
playwright-cli -s=test cookie-clear
```

### Auth state (save/load logged-in session)
```bash
playwright-cli -s=test state-save ./auth-state.json    # save after login
playwright-cli -s=test state-load ./auth-state.json    # restore in next session
```

---

## Performance Tracing

```bash
playwright-cli -s=test tracing-start
# ... perform the user flow ...
playwright-cli -s=test tracing-stop                        # output to stdout
playwright-cli -s=test tracing-stop --output trace.zip    # save to file

# View trace
npx playwright show-trace trace.zip
```

## Video Recording

```bash
playwright-cli -s=test video-start
# ... perform the flow ...
playwright-cli -s=test video-stop
```

---

## Network Mocking

```bash
playwright-cli -s=test route "*/api/users" --body '{"users":[]}' --status 200
playwright-cli -s=test route-list          # list active mocks
playwright-cli -s=test unroute "*/api/users"
playwright-cli -s=test unroute             # remove all mocks
```

---

## Session Management

```bash
playwright-cli list          # list all active sessions
playwright-cli close-all     # close all sessions gracefully
playwright-cli kill-all      # force-kill stale/zombie sessions
playwright-cli -s=test close # close specific session
playwright-cli -s=test delete-data  # delete session data (cookies, storage)
```

---

## playwright-cli vs browser-use

| Task | playwright-cli | browser-use |
|------|---------------|-------------|
| Scripted test steps | Preferred | Works |
| Network inspection | `network` | Not available |
| Console messages | `console` | Not available |
| Execute JS | `eval` | Not available |
| Performance tracing | `tracing-start/stop` | Not available |
| Storage inspection | `localstorage-*`, `cookie-*` | Not available |
| Autonomous goal completion | Needs scripting | Preferred |
| Real Chrome with existing login | `state-load` | `--browser real` |

**Rule:** Default to playwright-cli for all scripted and inspection tasks. Use browser-use only for autonomous/exploratory tasks where describing a goal is better than writing steps.
