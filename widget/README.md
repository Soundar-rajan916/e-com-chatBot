# Multilingual Regional E-Commerce Support Chat Widget

A lightweight, embeddable chat widget packaged as a standalone library that injects into any website via a single script tag (`<script src="/widget.js"></script>`).

---

## Features

- **Single Bundle**: Compiles to a single distribution file `dist/widget.js` (< 160 KB uncompressed, ~51 KB gzipped, well under the 180 KB budget).
- **Shadow DOM Isolation**: Renders entirely inside an open Shadow DOM (`#support-chat-widget-root`), ensuring complete style and DOM isolation from the host page.
- **Bilingual Regional Support**: Native Tamil (`ta`) and English (`en`) support with real-time language toggling.
- **Context Injection**: Dynamically binds to customer browsing context (e.g., viewing a specific product or viewing an order).
- **Session Claiming**: Transparently manages anonymous sessions (`support_anon` cookie) and claims conversation history upon customer authentication.
- **Rich Interactive Actions**: Handles structured actions from the support pipeline (e.g., `open_login`, `show_product`, `show_order`, `prompt_return`).
- **Dev & Debug Tooling**: Fully accessible via `/dev/chat` testbench in the host application.

---

## Embedding on Any Website

Place this snippet right before the closing `</body>` tag on any webpage:

```html
<!-- Regional E-Commerce Support Chat Widget -->
<script src="https://your-store.example.com/widget.js" defer></script>
<script>
  window.addEventListener("DOMContentLoaded", function () {
    if (window.SupportWidget) {
      window.SupportWidget.init({
        apiBaseUrl: "https://your-store.example.com",
        defaultOpen: false,
        theme: "light",
        language: "en"
      });
    }
  });
</script>
```

---

## JavaScript API Reference (`window.SupportWidget`)

The widget exposes a clean global interface on `window.SupportWidget`:

| Method | Parameters | Description |
|---|---|---|
| `init(config)` | `WidgetConfig` | Initializes and mounts the widget in the DOM. |
| `open()` | - | Expands the chat window. |
| `close()` | - | Minimizes the chat window into the floating launcher button. |
| `toggle()` | - | Toggles the chat window between open and closed. |
| `identify(customer)` | `{ customerId, name, email, phone }` | Informs the widget of an authenticated customer, claiming any anonymous session. |
| `setContext(context)` | `{ type, id, title }` | Sets the contextual state (e.g. `type: 'product'` or `type: 'order'`). |
| `clearContext()` | - | Clears the active contextual metadata. |
| `destroy()` | - | Unmounts the widget and cleans up DOM nodes and listeners. |

---

## Custom Events

Host pages can listen to lifecycle events emitted by the widget:

```javascript
window.addEventListener("support-widget:action", function (event) {
  const { action, payload } = event.detail;
  if (action === "open_login") {
    // Navigate or display login modal
    window.location.href = "/login";
  } else if (action === "show_product") {
    window.location.href = `/products/${payload.productId}`;
  }
});
```

---

## Local Development & Testing

```bash
# Install dependencies
npm --prefix widget install

# Run Vitest unit tests
npm --prefix widget test

# Build production bundle
npm --prefix widget run build
```
