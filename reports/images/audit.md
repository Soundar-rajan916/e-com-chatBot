# Product Image Audit Report

- **Total Products in Catalog**: 2120
- **Distinct Resolved Image URLs**: 1266
- **Total Duplicate Groups (images shared by >1 product)**: 32
- **Duplicate Groups Spanning Different Categories**: 10
- **Duplicate Groups Spanning Different Product Types**: 12
- **Average Products Per Image**: 1.7

## 1. Executive Summary & Root Cause Analysis

### Mechanism Causing Wrong and Reused Images
1. **Client-Side Naive Keyword Dictionary (`frontend/src/utils/productImages.ts`)**:
   The database `products` table has never stored real product image URLs. Instead, the backend API returns a placeholder SVG URL (`/api/products/{id}/image.svg`).
   To display photos in the storefront, `productImages.ts` intercepts image rendering using a hardcoded array `CURATED_PRODUCT_PHOTOS` containing only **~40 static Unsplash URLs** mapped via substring matching.

2. **Severe False-Positive Keyword Collisions**:
   - Substring matching `titleText.includes(kw)` creates disastrous false associations. For instance:
     - `cufflink` matches `https://images.unsplash.com/photo-1590736969955-71cc94801759` which actually depicts a **woman's wrist with a wristwatch and gold bracelet**.
     - `braided leather belt` matches `https://images.unsplash.com/photo-1553062407-98eeb64c6a62` which is actually an image of a **travel backpack**.
     - `oxford` in footwear matches `https://images.unsplash.com/photo-1549298916-b41d501d3772` which is a **red Nike sneaker**, completely wrong for formal leather Oxford dress shoes.
     - `dhotis_ethnic` products match `photo-1610030469983-98e550d6193c` which is a **woman in a wedding saree**, showing women's clothing for men's dhotis and lungis.

3. **Extreme Cardinality Collapse (2120 Products -> ~30 Images)**:
   Because 2,120 catalog items are matched against only ~30 distinct Unsplash URLs, hundreds of unique products share the EXACT same image. For example, over **500 formal shirts** share a single white shirt photo.

4. **No Verification Gate & No Backend Source of Truth**:
   Images were never verified with a Vision model to ensure the photo actually contains the advertised item, contains no people where inappropriate, has no third-party luxury logos, and has no duplicates across distinct products.

## 2. Top 10 Largest Duplicate Groups

| Image URL | Description | Product Count | Sample Products |
|---|---|---|---|
| `https://images.unsplash.com/photo-1617137984095-74e4e5e3613f...` | Accessories fallback | **285** | `AnnamFoods Artisanal Power Banks` (SKU-ELE-01028), `AnnamFoods Authentic Headphones` (SKU-ELE-01030), `AnnamFoods Authentic Mechanical Keyboards` (SKU-ELE-01124) and 282 more |
| `https://images.unsplash.com/photo-1610030469983-98e550d6193c...` | Woman in gold saree (MISMATCH for men's dhotis/lungi) | **98** | `Handloom Short Kurta` (SKU-MW-CSH-009), `Modern Handloom Short Kurta` (SKU-MW-CSH-024), `Artisan Handloom Checked Lungi` (SKU-SAR-00239) and 95 more |
| `https://images.unsplash.com/photo-1603808033192-082d6919d3e1...` | Sneakers (MISMATCH for sandals/chappal) | **68** | `Artisan Braided Leather Sandals` (SKU-FOO-00587), `Artisan Kolhapuri Leather Chappals` (SKU-FOO-00699), `Artisan Leather Cross Sandals` (SKU-FOO-00671) and 65 more |
| `https://images.unsplash.com/photo-1551028719-00167b16eac5?au...` | Suit jacket fallback | **49** | `Charcoal Suit Jacket` (SKU-MEN-00303), `Classic Single-Breasted Blazer` (SKU-MW-BLZ-012), `Essential Unstructured Linen Jacket` (SKU-MW-BLZ-004) and 46 more |
| `https://images.unsplash.com/photo-1596755094514-f87e34085b2c...` | White formal dress shirt | **49** | `Refined Slub Cotton Casual Shirt` (SKU-MW-CSH-021), `Refined Washed Denim Casual Shirt` (SKU-MW-CSH-035), `Signature Washed Denim Casual Shirt` (SKU-MW-CSH-020) and 46 more |
| `https://images.unsplash.com/photo-1533867617858-e7b97e060509...` | Footwear generic fallback | **41** | `Artisan Driving Moccasins` (SKU-FOO-00629), `Artisan Penny Leather Loafers` (SKU-FOO-00713), `Classic Driving Moccasins` (SKU-FOO-00704) and 38 more |
| `https://images.unsplash.com/photo-1521572267360-ee0c2909d518...` | Crewneck t-shirt | **40** | `ChettinadKitchen Classic Stainless Steel Vessels` (SKU-KIT-00847), `CholaStyle Authentic Stainless Steel Vessels` (SKU-KIT-00726), `CholaStyle Handwoven Stainless Steel Vessels` (SKU-KIT-00753) and 37 more |
| `https://images.unsplash.com/photo-1624378439575-d8705ad7ae80...` | Chinos / trousers | **37** | `Artisan Classic Khaki Chinos` (SKU-MEN-00375), `Artisan Navy Formal Trousers` (SKU-MEN-00338), `Charcoal Dress Pants` (SKU-MEN-00290) and 34 more |
| `https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf...` | Flannel/casual shirt | **29** | `Artisan Breezy Camp Collar Shirt` (SKU-MW-CSH-026), `Breezy Camp Collar Shirt` (SKU-MW-CSH-011), `Checked Flannel Shirt` (SKU-MW-CSH-013) and 26 more |
| `https://images.unsplash.com/photo-1549298916-b41d501d3772?au...` | Sneakers / dress shoes | **26** | `Artisan Derby Dress Shoes` (SKU-FOO-00657), `Classic Oxford Leather Shoes` (SKU-FOO-00577), `Derby Dress Shoes` (SKU-FOO-00567) and 23 more |

## 3. Duplicate Groups Spanning Different Categories

| Image URL | Description | Categories Spanned | Sample Products |
|---|---|---|---|
| `https://images.unsplash.com/photo-1598033129183-c4f50c736f10...` | Suit jacket/tie bar | accessories, blazers_suits | `Heritage Polished Brass Tie Bar` [accessories], `Polished Brass Tie Bar` [accessories], `Premium Polished Brass Tie Bar` [accessories], `Vintage Polished Brass Tie Bar` [accessories] |
| `https://images.unsplash.com/photo-1551028719-00167b16eac5?au...` | Suit jacket fallback | blazers_suits, sarees_ethnic | `Charcoal Suit Jacket` [blazers_suits], `Classic Single-Breasted Blazer` [blazers_suits], `Essential Unstructured Linen Jacket` [blazers_suits], `Handwoven Navy Wool Blazer` [blazers_suits] |
| `https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf...` | Flannel/casual shirt | casual_shirts, trousers_chinos | `Artisan Breezy Camp Collar Shirt` [casual_shirts], `Breezy Camp Collar Shirt` [casual_shirts], `Checked Flannel Shirt` [casual_shirts], `Classic Linen Mandarin Shirt` [casual_shirts] |
| `https://images.unsplash.com/photo-1610030469983-98e550d6193c...` | Woman in gold saree (MISMATCH for men's dhotis/lungi) | sarees_ethnic, dhotis_ethnic, casual_shirts | `Handloom Short Kurta` [casual_shirts], `Modern Handloom Short Kurta` [casual_shirts], `Artisan Handloom Checked Lungi` [dhotis_ethnic], `Artisan Handloom Checked Lungi` [dhotis_ethnic] |
| `https://images.unsplash.com/photo-1603252109303-2751441dd157...` | Striped shirt | formal_shirts, casual_shirts | `Handwoven Relaxed Striped Shirt` [casual_shirts], `Relaxed Striped Shirt` [casual_shirts], `Classic Pinstripe Business Shirt` [formal_shirts], `Fine Stripe Dress Shirt` [formal_shirts] |
| `https://images.unsplash.com/photo-1596755094514-f87e34085b2c...` | White formal dress shirt | formal_shirts, tshirts_polos, casual_shirts | `Refined Slub Cotton Casual Shirt` [casual_shirts], `Refined Washed Denim Casual Shirt` [casual_shirts], `Signature Washed Denim Casual Shirt` [casual_shirts], `Slub Cotton Casual Shirt` [casual_shirts] |
| `https://images.unsplash.com/photo-1617137984095-74e4e5e3613f...` | Accessories fallback | mobile_accessories, electronics_accessories | `AnnamFoods Artisanal Power Banks` [electronics_accessories], `AnnamFoods Authentic Headphones` [electronics_accessories], `AnnamFoods Authentic Mechanical Keyboards` [electronics_accessories], `AnnamFoods Classic Power Banks` [electronics_accessories] |
| `https://images.unsplash.com/photo-1603808033192-082d6919d3e1...` | Sneakers (MISMATCH for sandals/chappal) | footwear, pooja_items | `Artisan Braided Leather Sandals` [footwear], `Artisan Kolhapuri Leather Chappals` [footwear], `Artisan Leather Cross Sandals` [footwear], `Braided Leather Sandals` [footwear] |
| `https://images.unsplash.com/photo-1549298916-b41d501d3772?au...` | Sneakers / dress shoes | footwear, formal_shirts | `Artisan Derby Dress Shoes` [footwear], `Classic Oxford Leather Shoes` [footwear], `Derby Dress Shoes` [footwear], `Essential Derby Dress Shoes` [footwear] |
| `https://images.unsplash.com/photo-1521572267360-ee0c2909d518...` | Crewneck t-shirt | tshirts_polos, kitchenware | `ChettinadKitchen Classic Stainless Steel Vessels` [kitchenware], `CholaStyle Authentic Stainless Steel Vessels` [kitchenware], `CholaStyle Handwoven Stainless Steel Vessels` [kitchenware], `CoromandelAudio Artisanal Stainless Steel Vessels` [kitchenware] |

## 4. Duplicate Groups Spanning Different Product Types (Mismatches)

| Image URL | Description | Types Spanned | Sample Products |
|---|---|---|---|
| `https://images.unsplash.com/photo-1589756823695-278bc923f962...` | Tie / pocket square | pocket_square, bow_tie, necktie | `Artisan Linen Pocket Square` (pocket_square), `Artisan Silk Jacquard Necktie` (necktie), `Essential Woven Silk Bow Tie` (bow_tie), `Linen Pocket Square` (pocket_square) |
| `https://images.unsplash.com/photo-1606503829068-1964f4347781...` | Cardholder | money_clip, cardholder | `Classic Slim Leather Cardholder` (cardholder), `Engraved Money Clip` (money_clip), `Essential Engraved Money Clip` (money_clip), `Modern Engraved Money Clip` (money_clip) |
| `https://images.unsplash.com/photo-1598033129183-c4f50c736f10...` | Suit jacket/tie bar | tie_bar, blazers_suits, blazer | `Heritage Polished Brass Tie Bar` (tie_bar), `Polished Brass Tie Bar` (tie_bar), `Premium Polished Brass Tie Bar` (tie_bar), `Vintage Polished Brass Tie Bar` (tie_bar) |
| `https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf...` | Flannel/casual shirt | trousers, casual_shirt | `Artisan Breezy Camp Collar Shirt` (casual_shirt), `Breezy Camp Collar Shirt` (casual_shirt), `Checked Flannel Shirt` (casual_shirt), `Classic Linen Mandarin Shirt` (casual_shirt) |
| `https://images.unsplash.com/photo-1610030469983-98e550d6193c...` | Woman in gold saree (MISMATCH for men's dhotis/lungi) | sarees_ethnic, dhotis_ethnic, dhoti, kurta, waistcoat | `Handloom Short Kurta` (kurta), `Modern Handloom Short Kurta` (kurta), `Artisan Handloom Checked Lungi` (dhotis_ethnic), `Artisan Handloom Checked Lungi` (dhotis_ethnic) |
| `https://images.unsplash.com/photo-1603252109303-2751441dd157...` | Striped shirt | formal_shirt, casual_shirt | `Handwoven Relaxed Striped Shirt` (casual_shirt), `Relaxed Striped Shirt` (casual_shirt), `Classic Pinstripe Business Shirt` (formal_shirt), `Fine Stripe Dress Shirt` (formal_shirt) |
| `https://images.unsplash.com/photo-1596755094514-f87e34085b2c...` | White formal dress shirt | casual_shirt, t_shirt, polo_shirt, jeans, formal_shirt | `Refined Slub Cotton Casual Shirt` (casual_shirt), `Refined Washed Denim Casual Shirt` (jeans), `Signature Washed Denim Casual Shirt` (jeans), `Slub Cotton Casual Shirt` (casual_shirt) |
| `https://images.unsplash.com/photo-1617137984095-74e4e5e3613f...` | Accessories fallback | mobile_accessories, electronics_accessories | `AnnamFoods Artisanal Power Banks` (electronics_accessories), `AnnamFoods Authentic Headphones` (electronics_accessories), `AnnamFoods Authentic Mechanical Keyboards` (electronics_accessories), `AnnamFoods Classic Power Banks` (electronics_accessories) |
| `https://images.unsplash.com/photo-1614252235316-8c857d38b5f4...` | Double monk strap shoes (reused for brogues) | monk_strap, brogues | `Artisan Brogue Leather Shoes` (brogues), `Artisan Double Monk Strap Shoes` (monk_strap), `Brogue Leather Shoes` (brogues), `Classic Brogue Leather Shoes` (brogues) |
| `https://images.unsplash.com/photo-1549298916-b41d501d3772?au...` | Sneakers / dress shoes | derby_shoes, oxford_shoes | `Artisan Derby Dress Shoes` (derby_shoes), `Classic Oxford Leather Shoes` (oxford_shoes), `Derby Dress Shoes` (derby_shoes), `Essential Derby Dress Shoes` (derby_shoes) |

## 5. Architectural Fix in the New Pipeline

1. **Controlled Vocabulary & Type Normalization (`data/image_types.yml`)**:
   Normalize names (stripping marketing prefixes like 'Royal', 'Heritage', 'Handwoven') into canonical types (e.g. `cufflinks`, `leather_belt`, `oxford_shoes`, `silk_dhoti`).

2. **Official Provider API Retrieval (`ImageProvider`)**:
   Query Pexels / Unsplash with strict queries, aspect ratios, and rate limits, saving provider metadata (photographer, license, URL).

3. **Vision Model Gate (`VisionJudge`)**:
   Filter each candidate through Groq Llama 3.2 Vision. Verify the target item is clearly visible, reject luxury brand logos, reject inappropriate person poses, and enforce confidence >= 0.8.

4. **Perceptual Deduplication (`dHash` + Hamming Distance)**:
   Ensure visually identical images are not assigned across different products (Hamming distance > 6, max reuse <= 3 strictly within same type).

5. **Database Storage & API Serving**:
   Store verified image assignments in a new `product_images` table with photographer attribution and status. Serve `/api/products/{id}/image.svg` resolving to the verified image URL with SVG fallback.
