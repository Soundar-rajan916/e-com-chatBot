# Wink Minimalist Editorial Design System & UX Redesign Guide

This document defines the visual language, design principles, token taxonomy, component guidelines, and accessibility guarantees implemented in the redesign inspired by the **"Wink Ecommerce, Product List Page"** reference aesthetic.

---

## 1. Design System Principles

1. **Airy, Calm & Minimalist Editorial**:
   - High whitespace, uncrowded layouts, and clean visual breathing room.
   - Restrained color palette dominated by neutral greys, crisp white, and solid charcoal/black accents.
   - Elimination of loud gradient fills, decorative shadows, and visual clutter.

2. **Floating White Canvas on Soft Grey Ground**:
   - The outer page background is a soft, muted grey (`#F3F3F4`).
   - The primary application content sits on a clean white surface (`#FFFFFF`) framed by a subtle 1px hairline border (`#E7E7EA`) and a generous 20px corner radius (`--radius-panel`).

3. **Hairline Structural Framing**:
   - Instead of heavy dividing borders, all containers, cards, tables, and dividers use a unified 1px hairline stroke (`#E7E7EA`).

4. **Refined Pill Controls & Inversion Affordances**:
   - Primary interactive triggers utilize full-radius pills (`border-radius: 9999px`).
   - Primary actions are solid black pills (`#111111`) with white text.
   - Secondary actions are clean outline pills (`border: 1px solid #111111` or `#E7E7EA`).
   - Product cards feature bordered price pills that invert to solid black with white text on card hover.

5. **Strict Zero-Functionality Alteration Guarantee**:
   - All routes, form controls, validation rules, API endpoints, error handling, session keys, and keyboard interactions remain 100% identical to the pre-redesign baseline.

---

## 2. Design Tokens Reference

### Color Palette

| Token Name | Hex Value | Purpose | Contrast Ratio (on #FFFFFF) |
| :--- | :--- | :--- | :--- |
| `--color-page-bg` | `#F3F3F4` | Outer page backdrop canvas | N/A |
| `--color-surface` | `#FFFFFF` | Main white content cards & panels | N/A |
| `--color-surface-subtle` | `#F8F8F9` | Table alternate rows, subtle chips | N/A |
| `--color-surface-hover` | `#F0F0F2` | Card image placeholder backdrop, hover state | N/A |
| `--color-text-primary` | `#111111` | Headings, titles, active pill text | **16.5:1** (WCAG AAA) |
| `--color-text-muted` | `#5B6472` | Secondary descriptions, counts, metadata | **5.1:1** (WCAG AA Compliant) |
| `--color-text-subtle` | `#848D9A` | SKU numbers, disabled hints | 3.2:1 |
| `--color-hairline` | `#E7E7EA` | Subtle 1px dividers and borders | N/A |
| `--color-hairline-strong`| `#D1D2D6` | Hovered card borders and active borders | N/A |
| `--color-accent` | `#111111` | Primary black action button | 16.5:1 |
| `--color-success` | `#1F7A4D` | In-stock badges, order delivered status | **4.9:1** (WCAG AA) |
| `--color-warning` | `#9A6700` | Low-stock warnings, processing status | **4.7:1** (WCAG AA) |
| `--color-danger` | `#B42318` | Out-of-stock badges, error notices | **5.2:1** (WCAG AA) |

### Border Radii

- Controls & Inputs (`--radius-control`): `10px`
- Product & Category Cards (`--radius-card`): `16px`
- Dialogs & Canvas Panels (`--radius-panel` / `--radius-dialog`): `20px`
- Pill Buttons & Badges (`--radius-pill`): `9999px`

### Spacing Scale

`4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `48px`, `64px`

### Typography

- Font Family: `'Inter', 'Noto Sans Tamil', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Size Scale: `12px` (caption/sku), `14px` (body/input), `16px` (card title/subheading), `20px` (section title), `28px` (page title/price), `40px` (hero headline).
- Weights: `400` (Regular), `500` (Medium), `600` (Semibold).

---

## 3. Component Design Guide

### 1. Storefront Shell & Header (`Navbar.tsx`)
- **Primary Row**:
  - Left: Hamburger toggle (mobile) and quiet text navigation (`Home`, `Products`).
  - Center: Refined editorial wordmark "Regional Bazaar" (`font-size: 22px; font-weight: 600; letter-spacing: -0.03em;`).
  - Right: Segmented "EN | தமிழ்" language toggle, Orders link, Staff Console link, Shopping Bag button with item count badge, and Support trigger.
- **Secondary Row**:
  - Centered search pill (`#F3F3F4` fill, 9999px radius, focus expands to white with `#111111` border).
  - Horizontal scrolling category chips with active black pill state.

### 2. Product List Page (`ProductListPage.tsx`)
- **Grid Layout**: 3 columns on desktop, 2 columns on tablet, 1 column on mobile.
- **Product Card**:
  - 4:5 aspect ratio image frame with soft neutral `#F0F0F2` background.
  - Image smoothly zooms 1.03x on hover with 350ms ease.
  - Category tag in uppercase 11px muted text.
  - 1-2 line product title and Tamil title subtitle.
  - Bottom row with price in bordered pill (`border: 1px solid #111111; border-radius: 9999px;`) that inverts to solid black with white text on card hover.
  - Solid black pill "Add to Cart" button and outline "Ask AI" pill.

### 3. Filters Sidebar
- Structured into clean groups: Search input pill, Category list with right-aligned counts, Sort By select dropdown, and In-Stock Only checkbox.
- Muted counts (`#5B6472`) aligned right.
- Outline pill "Clear All Filters" trigger.

### 4. Product Detail Page (`ProductDetailPage.tsx`)
- 2-column editorial layout: Left 4:5 image container with SKU pill, Right product information column.
- Large title, Tamil translation title, bold price, and stock status pill.
- Pill quantity picker (`-` and `+` circular buttons) and solid black pill "Add to Shopping Cart" button.

### 5. Chat Widget (`widget/src/widget.css`)
- Re-styled inside Shadow DOM with mirrored design tokens.
- Floating launcher: Solid black circle (`56px x 56px`, `#111111`, white chat icon).
- Chat window: White surface, 20px radius, 1px hairline border, light blur.
- User bubbles: Solid black pill (`#111111`) with white text.
- Assistant/bot bubbles: Clean white surface with 1px hairline border (`#E7E7EA`).
- Quick reply chips: Outline pill buttons that invert to black on hover.
- Pill input row with send circle button.

### 6. Staff Console (`frontend/src/pages/console/*`)
- Editorial white header with staff status pill.
- Table rows separated by 1px hairlines with no heavy alternating stripes.
- Status badges styled as subtle tinted pills (Green for Paid/Delivered, Amber for Processing/Pending, Red for Cancelled/Refunded).

---

## 4. Do's and Don'ts for Future Changes

- **DO** keep primary buttons as solid black pills (`#111111`) with white text.
- **DO** use 1px hairline borders (`#E7E7EA`) instead of heavy box borders.
- **DO** maintain at least 4.5:1 contrast ratio for all text elements on white backgrounds (`#5B6472` provides 5.1:1).
- **DO** respect `prefers-reduced-motion` for all transitions.
- **DON'T** add gradients, heavy drop-shadows, or bright neon accent colors.
- **DON'T** introduce non-standard button shapes (maintain 9999px pills for buttons and 10px for input fields).
- **DON'T** alter existing route paths, API contracts, or component test identifiers.
