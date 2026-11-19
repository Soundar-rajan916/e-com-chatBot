# Image Provider Licensing and API Terms

This document records the verified terms of service, rate limits, attribution requirements, and technical constraints for image providers integrated into the product image pipeline, with **Pixabay** as the primary default provider.

---

## 1. Pixabay API (Primary Provider)

- **Official Website & Docs**: [https://pixabay.com/api/docs/](https://pixabay.com/api/docs/)
- **License**: [Pixabay Content License](https://pixabay.com/service/license-summary/) (Free for commercial and non-commercial use).

### Key Rules & Requirements
1. **Attribution (MANDATORY per API Terms)**:
   - When product images from Pixabay are displayed, the service must show a visible link to Pixabay (e.g. "Photos provided by Pixabay" in the footer and on product detail pages).
   - Photographer names are displayed as a courtesy when available: `Photo: [Photographer] / Pixabay`.
2. **NO HOTLINKING (MANDATORY)**:
   - **Pixabay explicitly forbids permanent hotlinking to its CDN URLs.**
   - **Self-Hosting Implementation**:
     - Candidate search preview images are accessed temporarily in-memory for vision verification and are never stored or exposed to clients.
     - **Only assigned images** (the single winning photo per product) are downloaded from Pixabay. Systematic mass downloading of candidate lists is strictly prohibited.
     - Downloaded images are resized locally via Pillow into optimized WebP formats:
       - Large version: max width/height 800px (`/media/products/{hash}_800.webp`).
       - Thumbnail version: max width/height 400px (`/media/products/{hash}_400.webp`).
     - WebP files are stored locally in the persistent media volume (`backend/media/products/`) and served directly by FastAPI and nginx with immutable cache headers.
     - No remote Pixabay URLs are ever returned to the storefront.
3. **Rate Limits**:
   - Limit: **100 requests per 60 seconds** per API key.
   - Response headers monitored:
     - `X-RateLimit-Limit`: Total allowed in window.
     - `X-RateLimit-Remaining`: Requests left in window.
     - `X-RateLimit-Reset`: Seconds remaining until reset.
   - The pipeline implements an async token bucket rate limiter and handles HTTP 429 with exponential backoff.
4. **Caching (MANDATORY)**:
   - Per Pixabay API terms, API search responses must be cached on disk for **at least 24 hours**.
   - Pipeline caches all responses under `data/image_cache/` with timestamps to satisfy this requirement.
5. **Generic Catalog Caveat**:
   - Pixabay has a generic stock catalog. Specific ethnic or regional items (e.g. dhotis, lungis, temple border silk sarees, specialized cufflinks) will often have no exact match. In accordance with the golden rule (**"A wrong image is worse than no image"**), these items must stay on the generated SVG placeholder rather than assigning a loose match.

---

## 2. Unsplash API (Optional Secondary Provider)

- **Official Website & Docs**: [https://unsplash.com/documentation](https://unsplash.com/documentation)
- **API Terms**: [https://unsplash.com/api-terms](https://unsplash.com/api-terms)

### Key Rules & Requirements
1. **Attribution**:
   - Attribution must be displayed: `Photo by [Photographer Name] on Unsplash` with UTM referral query parameters.
2. **Download Endpoint**:
   - Must send a GET request to `photo.links.download_location` on image selection.
3. **Rate Limits**:
   - Demo: 50 req/hr; Production: 5,000 req/hr.
