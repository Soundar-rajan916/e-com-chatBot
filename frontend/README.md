# Multilingual Regional E-Commerce Storefront & Staff Console

React 18 + TypeScript + Vite web application offering an end-to-end regional e-commerce store with integrated bilingual customer support, order management, return processing, and staff escalation console.

---

## Architecture & Structure

- **Storefront**:
  - `src/pages/store/HomePage.tsx`: Featured categories, trending products, policies.
  - `src/pages/store/ProductListPage.tsx`: Catalog browsing, filtering by price/stock, sorting, and contextual "Ask AI".
  - `src/pages/store/ProductDetailPage.tsx`: Bilingual product details, stock validation, and contextual chat launcher.
  - `src/pages/store/CartPage.tsx`: Line items with quantities, live price and stock validation, subtotal calculation.
  - `src/pages/store/CheckoutPage.tsx`: Address collection, payment choice (COD vs Demo Card), idempotency protection.
  - `src/pages/store/OrdersPage.tsx` & `OrderDetailPage.tsx`: Order history, status timeline, cancellation, and 7-day return request flow.
  - `src/pages/store/DevChatPage.tsx`: Route `/dev/chat` exercising the standalone support widget with context manipulation.
- **Staff Console (`/console`)**:
  - `src/pages/console/LoginPage.tsx`: Agent/Admin authentication with lockout protection.
  - `src/pages/console/InboxPage.tsx`: Real-time escalation queue, SLA overdue markers, priority/reason filters, stat tiles.
  - `src/pages/console/CaseDetailPage.tsx`: Full customer-bot-agent transcript, "Why this answer" trace inspector, refund approvals/rejections, and timeline.
- **Widget Integration**:
  - Chat interface is delivered via `widget/dist/widget.js`, mounted inside an isolated Shadow DOM on the storefront.

---

## Setup & Running (PowerShell)

```powershell
# Install dependencies
npm --prefix frontend install

# Run unit tests (Console + Storefront)
npm --prefix frontend test

# Run development server
npm --prefix frontend run dev
```

The frontend will run at `http://localhost:5173`.
