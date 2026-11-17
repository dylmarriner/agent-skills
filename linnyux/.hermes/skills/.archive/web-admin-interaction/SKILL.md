---
name: web-admin-interaction
description: Interact with web-based admin panels (routers, modems, NAS, switches, IoT config UIs) using Hermes built-in browser tools. Covers login flows, iframe-based content extraction, session expiry handling, and ref-ID instability patterns.
---

# Web Admin Panel Interaction

## When to Use

- Logging into a router/modem admin panel (192.168.x.x, 10.x.x.x, etc.)
- Navigating any HTTP-based admin interface that uses framesets or iframes for dynamic content
- Extracting connected device lists, WAN status, DHCP leases, or port mapping from admin UIs
- Any web form login where you need to supply credentials and scrape data from the resulting page

## Key Patterns

### 1. Login Flow

Admin panels typically have a simple form-based auth. The Hermes browser snapshot shows textboxes and clickable elements with ref IDs like `@e11`, `@e12`.

```
1. browser_navigate(url)                # Homepage usually redirects to /login.htm
2. browser_type(ref=@e12, text=pass)    # Type password into the password field
3. browser_click(ref=@e10)              # Click the Login button/link
4. browser_snapshot()                   # Should now show the main admin dashboard
```

**Pitfall:** The username is often pre-filled in a disabled textbox — don't try to type into it.

### 2. Session Expiry on Navigation

When you navigate back to a URL you were already logged into, the session may have expired and returned you to the login page. This happens because browser tools create a fresh page context.

**Detect it:** If after navigating or clicking, browser_snapshot returns to a login form, re-authenticate.

```
# After seeing login page again:
browser_type(ref=@e12, text=<password>)
browser_click(ref=@e10)
```

### 3. Ref ID Instability

Ref IDs (`@e1`, `@e12`, etc.) are **not persistent** — they change every page load. After any navigation, click, or form submission:

- **Always call browser_snapshot() first** to get fresh refs before interacting again
- Old refs from a prior snapshot WILL fail with "Unknown ref: eX"
- When a click fails with "Unknown ref", snapshot again and retry with the new ref

### 4. Iframe Content Extraction

Many admin panels render their content inside a single `<iframe>`. The browser_snapshot tool often shows only the iframe container, not its inner content — making it look like tables are empty when they actually contain data.

**Technique:** Use browser_console to reach inside the iframe's document:

```javascript
document.querySelector('iframe').contentDocument.body.innerText
```

This returns ALL the text content inside the iframe, including table rows, labels, and values that browser_snapshot couldn't see.

**For structured data extraction from tables:**

```javascript
// Extract table data from iframe as structured JSON
(function(){
  var doc = document.querySelector('iframe').contentDocument;
  var tables = doc.querySelectorAll('table');
  var results = [];
  tables.forEach(function(t, idx){
    var header = t.closest('td')
      ? (t.closest('td').previousElementSibling
        ? t.closest('td').previousElementSibling.textContent.trim()
        : 'table-'+idx)
      : 'table-'+idx;
    var rows = [];
    t.querySelectorAll('tr').forEach(function(tr){
      var cells = [];
      tr.querySelectorAll('th, td').forEach(function(td){
        cells.push(td.textContent.trim());
      });
      if(cells.length) rows.push(cells);
    });
    if(rows.length) results.push({section: header, rows: rows});
  });
  return JSON.stringify(results, null, 2);
})()
```

**If that returns empty (single-frame IFrame document replacement pattern):**

Some routers write data directly into the iframe via `document.write()` or `srcdoc`. In those cases, browser_snapshot (not browser_vision) with `full=true` may show more content. Also try:

```javascript
document.querySelector('iframe').contentDocument.body.innerHTML.substring(0, 5000)
```

### 5. When browser_vision Fails

On some model providers, browser_vision may error (the model doesn't support image_url content). The screenshot is still saved — you can reference the path from the error's `screenshot_path` field. But for data extraction, fall back to browser_console with JS expressions.

### 6. Common Admin Panel Layouts

| Layout Type | How to Extract Data |
|---|---|
| **Iframe + nested tables** | `iframe.contentDocument.body.innerText` via console |
| **Single page, no iframes** | browser_snapshot(full=true) usually works |
| **AJAX-loaded tables** | Click "Refresh" first, then extract via console |
| **Separate device/monitor pages** | Navigate to specific sub-URLs (e.g., /devices.htm, /status.htm) |
| **JSON API behind the UI** | Check network tab for XHR endpoints returning JSON |

## Pitfalls

- **Ref IDs change on every page load** — always re-snapshot after navigation
- **iframe.contentDocument may be null** if CORS blocks it (same-origin only — works on router admin panels since the iframe loads from the same IP)
- **"Refresh" links in admin panels** often trigger AJAX reloads of the iframe content — clicking them may make data appear that wasn't there before
- **Disabled input fields** (like the username on router login pages) cannot be typed into — don't attempt it
- **browser_vision may fail on non-vision models** — always have a browser_console fallback ready
- **Session cookies may not persist across page navigations** — if redirected to login after clicking a nav item, re-login and try again
- **Some tables are in nested frames** — you may need `document.querySelector('iframe').contentDocument.querySelector('iframe')` for double-nested frames
