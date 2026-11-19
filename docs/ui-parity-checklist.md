# UI Parity Checklist & Baseline Inventory

This document defines the functional baseline and parity matrix for the **Regional Bazaar** e-commerce application (Storefront, Chat Widget, and Staff Support Console). Every route, control, form validation, keyboard shortcut, accessible role, storage key, API call, and translation string listed here must remain 100% functionally identical throughout and after the visual redesign.

---

## 1. Test Suite Baseline Counts

| Test Suite | Files | Tests Total | Passed | Skipped | Failed | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Suite (`pytest`)** | 14 | 52 | 48 | 3 | 1* | *Backend code is strictly untouched per instructions. Live Groq tests skipped without live API key in test runner.* |
| **Storefront (`frontend vitest`)** | 2 | 6 | 6 | 0 | 0 | 100% green |
| **Chat Widget (`widget vitest`)** | 1 | 4 | 4 | 0 | 0 | 100% green |
| **Combined Frontend Tests** | **3** | **10** | **10** | **0** | **0** | **100% passing baseline** |

---

## 2. Global State, Storage Keys & Public APIs

### 2.1 Storage Keys
- `sessionStorage.getItem('cart_session_id')`: Persists guest / active customer cart ID across refreshes.
- `sessionStorage.getItem('auth_token')`: Stores customer JWT authentication token.
- `localStorage.getItem('support_widget_session')`: Persists chat session ID in the embedded widget.
- `localStorage.getItem('support_widget_locale')`: Stores user-selected widget locale (`en` | `ta`).

### 2.2 Chat Widget Public API (`window.SupportWidget`)
- `SupportWidget.init(config)`: Mounts widget into `#support-widget-host` using Shadow DOM (`open` mode).
  - Supported config keys: `storeName`, `defaultOpen`, `apiUrl`.
- `SupportWidget.open()`: Expands the chat window; fires `widget:opened` CustomEvent.
- `SupportWidget.close()`: Minimizes the chat window; fires `widget:closed` CustomEvent.
- `SupportWidget.isOpen()`: Returns boolean indicating open state.
- `SupportWidget.setContext(context)`: Sets product or order context pill (`type`, `id`, `title`).
- `SupportWidget.setLocale(locale)`: Switches UI language between English (`en`) and Tamil (`ta`).
- `SupportWidget.identify(customer)`: Associates customer session with `name`, `phone`, `email`.
- `SupportWidget.destroy()`: Cleans up DOM, event listeners, and timer loops leaving zero DOM footprint.

---

## 3. Storefront Pages & Component Matrix

### 3.1 App Shell & Navigation (`Navbar.tsx`, `Footer.tsx`)
- **Route**: Rendered across all non-console routes (`/`, `/products`, `/cart`, etc.).
- **Controls**:
  - Store Wordmark / Logo link -> Navigates to `/`
  - "Products" / "பொருட்கள்" nav link -> Navigates to `/products`
  - Search Input -> Submits search query `q` to `/products?q=...` on Enter
  - Cart Icon Button -> Displays live cart badge with count (`.cart-badge`); navigates to `/cart`
  - Account / Login link -> Navigates to `/account` (if authenticated) or `/login`
  - Language Segmented Toggle -> "EN \| தமிழ்" switches global display language
  - Mobile Menu Hamburger Button -> Toggles responsive navigation drawer
- **Network Requests**:
  - `GET /api/config`
  - `GET /api/health`
  - `GET /api/cart`
  - `GET /api/auth/me`

### 3.2 Home Page (`HomePage.tsx`)
- **Route**: `/`
- **Controls**:
  - Hero Callout CTA ("Browse Collection" / "பொருட்களைப் பார்க்க") -> Navigates to `/products`
  - Category Pills / Cards -> Filter `/products?category=...`
  - Featured Product Cards -> Navigates to `/products/:id`
  - "Add to Cart" button on featured items -> Dispatches `POST /api/cart/items`
  - "Ask AI" button on product cards -> Invokes `SupportWidget.open()` with product context
- **Visible Strings**:
  - English: "Regional Bazaar", "Experience the Finest Products of Tamil Nadu", "Browse Collection", "Featured Heritage Products", "Add to Cart", "Ask AI"
  - Tamil: "பொருட்கள்", "தமிழ்நாட்டின் சிறந்த பொருட்கள்", "கார்ட்டில் சேர்", "AI உதவி"
- **Network Requests**:
  - `GET /api/categories`
  - `GET /api/products?page=1&page_size=8`

### 3.3 Product List Page (`ProductListPage.tsx`)
- **Route**: `/products`
- **URL Parameters**:
  - `q`: Search string query
  - `category`: Selected category filter
  - `min_price`, `max_price`: Price filter range
  - `in_stock_only`: Boolean (`true` / `false`)
  - `sort`: `newest` \| `price_asc` \| `price_desc` \| `rating_desc`
  - `page`: Integer page number
- **Controls**:
  - Category Filter Checkboxes / Pills (with live facet count chips)
  - Price Range Slider / Inputs
  - In-Stock Only Toggle Switch
  - "Clear All Filters" button
  - Sort Dropdown (`sort` parameter)
  - Product Card link -> Navigates to `/products/:id` (accessible role: link)
  - Pagination Controls ("Previous", "Next", Page numbers)
- **Keyboard Behaviour**:
  - Enter / Space selects category checkboxes and filter toggles.
  - Tab traverses through product cards with single tab-stop per card.
- **Network Requests**:
  - `GET /api/categories`
  - `GET /api/products?q=...&category=...&min_price=...&max_price=...&in_stock_only=...&sort=...&page=...`

### 3.4 Product Detail Page (`ProductDetailPage.tsx`)
- **Route**: `/products/:id`
- **Controls**:
  - Breadcrumb navigation (`Home > Products > [Product Title]`)
  - Quantity Increment / Decrement Stepper (`-`, `+`)
  - "Add to Cart" Primary Button (Disabled when out of stock; tooltip shows stock status)
  - "Ask AI Assistant" Button (Sets context in widget)
  - Related Products Grid (Navigates to related item)
- **Form Fields & Validation**:
  - Quantity: Minimum 1, Maximum = available `stock_qty`.
- **Visible Strings**:
  - English: "In Stock", "Out of Stock", "Quantity", "Add to Cart", "Related Products", "Description", "Specifications"
  - Tamil: "கையிருப்பில் உள்ளது", "கையிருப்பில் இல்லை", "அளவு", "கார்ட்டில் சேர்", "விளக்கம்"
- **Network Requests**:
  - `GET /api/products/:id`
  - `GET /api/products/:id/related`
  - `POST /api/cart/items`

### 3.5 Cart Page (`CartPage.tsx`)
- **Route**: `/cart`
- **Controls**:
  - Item Quantity Stepper (`-`, `+`)
  - Item Remove Button (`×` or "Remove")
  - "Continue Shopping" link -> Navigates to `/products`
  - "Proceed to Checkout" Primary Button (Disabled if cart has out-of-stock items)
  - Problem Warning Banners (Displays if an item exceeds available inventory)
- **Network Requests**:
  - `GET /api/cart`
  - `PATCH /api/cart/items/:id`
  - `DELETE /api/cart/items/:id`

### 3.6 Checkout Page (`CheckoutPage.tsx`)
- **Route**: `/checkout`
- **Form Fields & Validation Rules**:
  - Full Name: Required, min 2 chars.
  - Email: Required, valid email format.
  - Phone: Required, valid 10-digit phone number format (+91 prefix supported).
  - Shipping Address: Required.
  - City: Required.
  - State: Required (defaults to "Tamil Nadu").
  - PIN Code: Required, 6 digits.
  - Payment Method: Radio cards (`demo_card`, `upi`, `cod`).
- **Idempotency Guard**: Submit button disables immediately on click and prevents double-submission while processing.
- **Network Requests**:
  - `GET /api/cart`
  - `POST /api/orders` (with `Idempotency-Key` header)

### 3.7 Orders & Order Detail Pages (`OrdersPage.tsx`, `OrderDetailPage.tsx`)
- **Routes**: `/orders`, `/orders/:orderNumber`
- **Controls**:
  - Order Status Badges (`placed`, `processing`, `shipped`, `delivered`, `cancelled`)
  - Order Stage Tracking Timeline
  - "Request Return / Refund" Dialog Trigger
  - Return Reason Select Dropdown & Return Description textarea
  - Cancel Order Button (Active only before dispatch/shipping)
- **Dialogs & Keyboard Trap**:
  - Modal dialog traps focus with Escape key dismissing the dialog.
- **Network Requests**:
  - `GET /api/orders`
  - `GET /api/orders/:orderNumber`
  - `POST /api/orders/:orderNumber/cancel`
  - `POST /api/refunds`

### 3.8 Auth Pages (`CustomerLoginPage.tsx`, `CustomerRegisterPage.tsx`, `AccountPage.tsx`)
- **Routes**: `/login`, `/register`, `/account`
- **Form Fields & Validation**:
  - Login: Email & Password required.
  - Register: Full Name, Email, Phone (+91), Preferred Language (`en` \| `ta` \| `tanglish`), Password (min 8 chars).
  - Account: Change password fields, View past orders, WhatsApp Notification Card toggle.
- **Network Requests**:
  - `POST /api/auth/login`
  - `POST /api/auth/register`
  - `GET /api/auth/me`
  - `POST /api/auth/change-password`

---

## 4. Staff Support Console (`/console/*`)

### 4.1 Console Login (`/console/login`)
- **Controls**: Email, Password, Quick-fill Demo Admin / Support Agent buttons, "Sign In to Console".
- **Network Requests**: `POST /api/admin/auth/login`

### 4.2 Console Inbox & Orders (`/console`)
- **Tabs**: "All Orders" (`tab=orders`), "Refunds" (`tab=refunds`), "Cases" (`tab=cases`).
- **Controls**:
  - Search input: Filters order number, customer name, email, phone.
  - "Push to Processing ➔" advance stage button.
  - Cancel Order button.
  - "✓ Approve Refund" button.
- **Network Requests**:
  - `GET /api/admin/auth/me`
  - `GET /api/admin/orders`
  - `POST /api/admin/orders/:orderNumber/advance`
  - `POST /api/admin/orders/:orderNumber/cancel`
  - `GET /api/admin/refunds`
  - `POST /api/admin/refunds/:id/approve`

---

## 5. Verification Checklist

- [x] Baseline backend tests executed and recorded.
- [x] Baseline storefront vitest executed: 6/6 passed.
- [x] Baseline widget vitest executed: 4/4 passed.
- [x] Baseline screenshots checklist captured under `docs/ui-redesign/before/`.
- [ ] Minimalist tokens created in `frontend/src/styles/tokens.css`.
- [ ] Base typography and resets in `frontend/src/styles/base.css`.
- [ ] SVG icons module in `frontend/src/components/icons.tsx`.
- [ ] Storefront App Shell, Header, Search & Navigation restyled.
- [ ] Home Page, Hero & Featured Cards restyled.
- [ ] Product List Page, Filter Sidebar, Product Cards & Pagination restyled.
- [ ] Product Detail Page & Stepper restyled.
- [ ] Cart & Checkout two-column layout restyled.
- [ ] Orders list, Detail timeline & Return dialogs restyled.
- [ ] Chat Widget Shadow DOM restyled with identical token palette.
- [ ] Staff Console restyled to match editorial aesthetic.
- [ ] Full regression verification across English & Tamil, desktop (1440/1280), tablet (768), and mobile (360).
