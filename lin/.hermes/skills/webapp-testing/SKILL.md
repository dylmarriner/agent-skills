---
name: webapp-testing
description: Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.
---

# Web Application Testing

This skill enables comprehensive testing and debugging of local web applications using Playwright automation.

Prefer a real browser session for interactive and visual QA. Use Playwright MCP or Browser Use (`browser_exec`) when available; isolate the run in a named session so clicks, localStorage, and consent choices do not alter the user's live browser state. If neither is available, use Playwright in a local Node.js environment.

## When to Use This Skill

Use this skill when you need to:

- Test frontend functionality in a real browser
- Verify UI behavior and interactions
- Debug web application issues
- Capture screenshots for documentation or debugging
- Inspect browser console logs
- Validate form submissions and user flows
- Check responsive design across viewports

## Prerequisites

- Node.js installed on the system
- A locally running web application (or accessible URL)
- Playwright will be installed automatically if not present

## Core Capabilities

### 1. Browser Automation

- Navigate to URLs
- Click buttons and links
- Fill form fields
- Select dropdowns
- Handle dialogs and alerts

### 2. Verification

- Assert element presence
- Verify text content
- Check element visibility
- Validate URLs
- Test responsive behavior

#### Responsive visual verification

1. Confirm the app is serving the expected build, then open it in an isolated browser session.
2. Inspect a representative desktop viewport (1440×900) and phone viewport (390×844). With Browser Use, set these via `cdp('Emulation.setDeviceMetricsOverride', width=..., height=..., deviceScaleFactor=1, mobile=...)`; confirm the effective dimensions with `page_info()`.
3. At each viewport, capture and inspect the actual screenshot (`print(capture_screenshot())` in Browser Use). Also compare `document.documentElement.scrollWidth` with `innerWidth` and inspect visible text; DOM checks and dimensions supplement, but never replace, visual inspection.
4. Exercise the changed user flow with accessible/visible controls and verify the resulting state (for example, the selected model label or active marker), not merely that the click returned. Keep interaction tests minimal; avoid real purchases, costly requests, analytics opt-ins, or public-sharing actions. Use privacy-preserving choices in consent prompts.
5. Record the viewport and observed result, and distinguish a defect in the changed surface from a pre-existing issue elsewhere on the page. Do not expand a targeted visual check into a general redesign unless requested.

### 3. Debugging

- Capture screenshots
- View console logs
- Inspect network requests
- Debug failed tests

## Usage Examples

### Example 1: Basic Navigation Test

```javascript
// Navigate to a page and verify title
await page.goto("http://localhost:3000");
const title = await page.title();
console.log("Page title:", title);
```

### Example 2: Form Interaction

```javascript
// Fill out and submit a form
await page.fill("#username", "testuser");
await page.fill("#password", "password123");
await page.click('button[type="submit"]');
await page.waitForURL("**/dashboard");
```

### Example 3: Screenshot Capture

```javascript
// Capture a screenshot for debugging
await page.screenshot({ path: "debug.png", fullPage: true });
```

## Guidelines

1. **Always verify the app is running** - Check that the local server is accessible before running tests
2. **Use explicit waits** - Wait for elements or navigation to complete before interacting
3. **Capture screenshots on failure** - Take screenshots to help debug issues
4. **Clean up resources** - Always close the browser when done
5. **Handle timeouts gracefully** - Set reasonable timeouts for slow operations
6. **Test incrementally** - Start with simple interactions before complex flows
7. **Use selectors wisely** - Prefer data-testid or role-based selectors over CSS classes

## Common Patterns

### Pattern: Wait for Element

```javascript
await page.waitForSelector("#element-id", { state: "visible" });
```

### Pattern: Check if Element Exists

```javascript
const exists = (await page.locator("#element-id").count()) > 0;
```

### Pattern: Get Console Logs

```javascript
page.on("console", (msg) => console.log("Browser log:", msg.text()));
```

### Pattern: Handle Errors

```javascript
try {
  await page.click("#button");
} catch (error) {
  await page.screenshot({ path: "error.png" });
  throw error;
}
```

## Limitations

- Requires Node.js environment
- Cannot test native mobile apps (use React Native Testing Library instead)
- May have issues with complex authentication flows
- Some modern frameworks may require specific configuration

## Helper Functions

Some helper functions are available in [`test-helper.js`](./assets/test-helper.js) to simplify common tasks like waiting for elements, capturing screenshots, and handling errors. You can import and use these functions in your tests to improve readability and maintainability.
