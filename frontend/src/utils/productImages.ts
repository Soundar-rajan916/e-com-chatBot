import { getBaseUrl } from '../api/client';

// Curated high-resolution lifestyle product photos deterministically matched by product title & subcategory keywords
const CURATED_PRODUCT_PHOTOS: Array<{ keywords: string[]; url: string }> = [
  // --- SPECIALIZED ACCESSORIES (Title-First Precise Matching) ---
  {
    keywords: ['cufflink', 'cufflinks', 'clifflinks', 'silver cufflinks', 'royal silver cufflinks', 'handwoven silver cufflinks'],
    url: 'https://images.unsplash.com/photo-1590736969955-71cc94801759?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['chronograph', 'wristwatch', 'leather watch', 'timepiece', 'watch'],
    url: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['cardholder', 'card holder', 'slim leather cardholder'],
    url: 'https://images.unsplash.com/photo-1606503829068-1964f4347781?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['money clip', 'engraved money clip'],
    url: 'https://images.unsplash.com/photo-1606503829068-1964f4347781?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['wallet', 'bifold', 'billfold', 'leather bifold wallet'],
    url: 'https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['braided leather belt', 'braided belt', 'heritage braided leather belt'],
    url: 'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['reversible leather belt', 'reversible belt', 'essential reversible leather belt'],
    url: 'https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['leather belt', 'belt'],
    url: 'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tie bar', 'tie clip', 'polished brass tie bar'],
    url: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pocket square', 'linen pocket square'],
    url: 'https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['bow tie', 'silk bow tie', 'woven silk bow tie'],
    url: 'https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['necktie', 'jacquard necktie', 'silk jacquard', 'tie'],
    url: 'https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80',
  },

  // --- SPECIALIZED BLAZERS & SUITS (Title-First Precise Matching) ---
  {
    keywords: ['waistcoat', 'tailored waistcoat', 'suit vest', 'formal vest'],
    url: 'https://images.unsplash.com/photo-1592878904946-b3cd8ae243d0?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tuxedo', 'black tuxedo jacket', 'tuxedo jacket', 'tux'],
    url: 'https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['houndstooth', 'houndstooth wool jacket'],
    url: 'https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['double-breasted', 'double-breasted blazer', 'double breasted'],
    url: 'https://images.unsplash.com/photo-1591561954557-26941169b49e?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['single-breasted', 'single-breasted blazer', 'single breasted', 'classic single-breasted'],
    url: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tweed', 'classic tweed blazer', 'tweed blazer'],
    url: 'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['bandhgala', 'nehru jacket', 'nehru coat', 'raw silk nehru'],
    url: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['charcoal suit jacket', 'navy wool blazer', 'blazer', 'suit', 'jacket'],
    url: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80',
  },

  // --- FOOTWEAR (Title-First Precise Matching) ---
  {
    keywords: ['running', 'running shoes', 'cushioned running'],
    url: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['sneaker', 'sneakers', 'white leather sneaker'],
    url: 'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['penny loafer', 'penny leather loafer'],
    url: 'https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tassel loafer', 'tassel leather loafer'],
    url: 'https://images.unsplash.com/photo-1582895181348-29b1ca1f52d5?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['monk strap', 'double monk strap'],
    url: 'https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['brogue', 'brogues', 'brogue leather shoes'],
    url: 'https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['derby', 'derby dress shoes'],
    url: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['oxford', 'oxford leather shoes'],
    url: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['kolhapuri', 'peshawari', 'chappal', 'sandals', 'sandal', 'cross sandals'],
    url: 'https://images.unsplash.com/photo-1603808033192-082d6919d3e1?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['moccasin', 'driving moccasins', 'slip-on mule', 'suede slip-on', 'loafer', 'shoes', 'shoe', 'footwear'],
    url: 'https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=600&q=80',
  },

  // --- DHOTIS & ETHNIC WEAR ---
  {
    keywords: ['kanchipuram', 'mayilkann', 'zari', 'gold zari', 'kasavu', 'temple border', 'double layer', 'panchakacham', 'coimbatore', 'vesti', 'veshti', 'dhoti', 'angavastram', 'lungi', 'kurta'],
    url: '/images/products/silk_dhoti_men.webp',
  },

  // --- CASUAL SHIRTS ---
  {
    keywords: ['linen shirt', 'summer linen', 'cuban collar', 'camp collar', 'short sleeve linen'],
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['chambray', 'indigo chambray', 'safari', 'utility', 'flannel', 'plaid', 'mandarin', 'raw cotton'],
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80',
  },

  // --- FORMAL SHIRTS ---
  {
    keywords: ['pinstripe', 'stripe dress shirt', 'fine stripe', 'striped shirt'],
    url: 'https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['french cuff', 'cutaway', 'spread collar', 'herringbone', 'twill', 'poplin', 'oxford shirt', 'giza cotton', 'pinpoint', 'dress shirt', 'formal shirt', 'shirt'],
    url: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80',
  },

  // --- TROUSERS & CHINOS ---
  {
    keywords: ['jeans', 'denim', 'selvedge'],
    url: 'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['cargo', 'cargo pants'],
    url: 'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['pleated', 'dress trousers', 'wool trousers', 'dress pants'],
    url: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['chinos', 'khaki', 'gurkha', 'drawstring', 'trousers', 'pants'],
    url: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80',
  },

  // --- POLOS & TEES ---
  {
    keywords: ['henley', 'waffle'],
    url: 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['polo', 'pique', 'mercerized', 'striped polo', 'zip neck polo'],
    url: 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tee', 't-shirt', 'tshirt', 'crewneck', 'supima'],
    url: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&q=80',
  },

  // --- GENERAL CATEGORY FALLBACKS ---
  {
    keywords: ['formal_shirts'],
    url: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['casual_shirts'],
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['blazers_suits'],
    url: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['dhotis_ethnic'],
    url: '/images/products/silk_dhoti_men.webp',
  },
  {
    keywords: ['footwear'],
    url: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['trousers_chinos'],
    url: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tshirts_polos'],
    url: 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['accessories', 'accessory'],
    url: 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=600&q=80',
  },
];

export const HERO_SHOWCASE_PHOTOS = {
  silkDhoti: '/images/products/silk_dhoti_men.webp',
  blazer: 'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=85',
  linenShirt: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=85',
  leatherShoes: 'https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&q=85',
  // Backward-compatible keys
  silkSaree: '/images/products/silk_dhoti_men.webp',
  cookware: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=85',
  filterCoffee: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=85',
  nativeSpices: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=85',
};

export const PROMO_BANNER_PHOTOS = {
  weddingSilks: '/images/products/silk_dhoti_men.webp',
  summerLinen: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=800&q=85',
  leatherShoes: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=800&q=85',
  // Backward-compatible keys
  handloom: '/images/products/silk_dhoti_men.webp',
  cookware: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=800&q=85',
  spices: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=800&q=85',
};

export const TESTIMONIAL_AVATARS = {
  karthik: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80',
  arvind: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80',
  michael: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=200&q=80',
  // Backward-compatible keys
  sarah: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80',
  priya: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80',
};

export const CATEGORY_PHOTOS: Record<string, string> = {
  'formal_shirts': 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=400&q=80',
  'casual_shirts': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=400&q=80',
  'tshirts_polos': 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=400&q=80',
  'trousers_chinos': 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=400&q=80',
  'blazers_suits': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'dhotis_ethnic': '/images/products/silk_dhoti_men.webp',
  'footwear': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
  'accessories': 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=400&q=80',
  'Formal Shirts': 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=400&q=80',
  'Casual Linen': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=400&q=80',
  'Dhotis & Ethnic': '/images/products/silk_dhoti_men.webp',
  'Dhotis & Veshtis': '/images/products/silk_dhoti_men.webp',
  'Trousers & Chinos': 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=400&q=80',
  'Blazers & Suits': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Polos & T-Shirts': 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=400&q=80',
  'Footwear & Loafers': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
  'Accessories': 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=400&q=80',
  'mens_wear': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'View All': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  // Backward-compatible aliases
  'Handloom & Silks': '/images/products/silk_dhoti_men.webp',
  'Cookware': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Spices & Masalas': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=400&q=80',
  'Heritage Grains': 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=400&q=80',
  'Filter Coffee': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Traditional Sweets': 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=400&q=80',
  'Artisan Crafts': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
};

// Optional S3 / CloudFront CDN base URL override
const S3_ASSETS_BASE_URL = (import.meta.env.VITE_S3_ASSETS_BASE_URL || '').trim();

/**
 * Returns a high quality product photo URL matching the product title/category.
 * If no photo matches or if loading fails, it falls back to the backend SVG vector endpoint.
 */
export function getProductImageUrl(product: {
  id?: string;
  sku?: string;
  title?: string;
  name_en?: string;
  category?: string;
  image_url?: string;
  image_status?: string;
}): string {
  // 1. Direct CloudFront or Amazon S3 URL
  if (product.image_url && product.image_url.startsWith('http')) {
    return product.image_url;
  }

  // 2. If VITE_S3_ASSETS_BASE_URL is provided and image is relative /media/products/
  if (S3_ASSETS_BASE_URL && product.image_url && product.image_url.startsWith('/media/products/')) {
    const cleanBase = S3_ASSETS_BASE_URL.replace(/\/+$/, '');
    return `${cleanBase}/${product.image_url.replace('/media/', '')}`;
  }

  // 3. If backend returned a verified or override image from the pipeline
  if (product.image_status === 'verified' || product.image_status === 'override') {
    if (product.image_url && product.image_url.startsWith('/media/')) {
      return `${getBaseUrl()}${product.image_url}`;
    }
  }

  // 3. Curated lifestyle photography for menswear
  const titleText = `${product.title || ''} ${product.name_en || ''} ${product.category || ''} ${product.sku || ''}`.toLowerCase();
  for (const item of CURATED_PRODUCT_PHOTOS) {
    if (item.keywords.some((kw) => titleText.includes(kw))) {
      return item.url;
    }
  }

  // 4. Self-hosted media URL fallback
  if (product.image_url && product.image_url.startsWith('/media/')) {
    return `${getBaseUrl()}${product.image_url}`;
  }

  // 5. Fallback to backend dynamic SVG vector placeholder
  if (product.image_url && product.image_url.startsWith('/api/products/')) {
    return `${getBaseUrl()}${product.image_url.replace('/api', '')}`;
  }
  if (product.id) {
    return `${getBaseUrl()}/products/${product.id}/image.svg`;
  }

  return '/images/categories/formal_shirts.svg';
}

/**
 * Fallback handler for img elements to switch to SVG endpoint on error.
 */
export function handleProductImageError(
  e: React.SyntheticEvent<HTMLImageElement, Event>,
  productId?: string
) {
  const target = e.currentTarget;
  const fallbackUrl = productId
    ? `${getBaseUrl()}/products/${productId}/image.svg`
    : '/images/categories/formal_shirts.svg';

  if (target.src !== fallbackUrl && !target.src.endsWith(fallbackUrl)) {
    target.src = fallbackUrl;
  }
}
