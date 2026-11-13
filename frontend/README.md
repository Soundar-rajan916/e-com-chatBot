# Multilingual Regional E-Commerce Support Assistant - Frontend (Phase 2)

React 18 + TypeScript + Vite frontend client for customer support in English, Tamil (தமிழ்), and Tanglish, featuring grounded source citations and multilingual conversational UI.

---

## 1. Prerequisites

- **Node.js**: v20+ (tested on Node v24.14.0)
- **npm**: v10+ (tested on npm 11.14.0)
- **Backend API**: Running at `http://127.0.0.1:8000` (FastAPI)

---

## 2. Setup & Installation (PowerShell)

```powershell
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment variables
Copy-Item .env.example .env
```

---

## 3. Configuration

By default, the frontend connects to `http://127.0.0.1:8000`. To point to a different backend:
Edit `frontend/.env`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 4. Running the Development Server

```powershell
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 5. Verification & Testing

```powershell
# Run unit & integration tests with Vitest + React Testing Library (11 tests)
npm test

# Run ESLint validation (0 warnings, 0 errors)
npm run lint

# Production build check (TypeScript strict mode + Vite bundling)
npm run build
```

---

## 6. Features & Grounded Sources Display

- **Grounded Source Attribution**: When the assistant answers policy or product inquiries via RAG, retrieved items are cited in the message disclosure under "Sources", labeled with `[policy]` or `[product]` badges and exact titles.
- **Multilingual Script Support**: Full native Unicode support for Tamil script (`\u0B80` to `\u0BFF`) and Romanized Tanglish with zero text truncation or distortion.
- **Observability**: Collapsible Details disclosure shows detected Intent, Language, Trace ID, and Retrieved Sources.
- **Resilience**: Real-time health banner indicator polling `/health` every 10 seconds, and retry buttons on network or server timeouts.
- **No Third-Party Component Bloat**: Built purely with vanilla modern CSS (custom properties, responsive grid/flexbox, zero Tailwind/MUI).
