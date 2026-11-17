import { getBaseUrl } from '../api/client';

// Curated high-resolution lifestyle product photos for key catalog types (100% Men's Wear focus)
const CURATED_PRODUCT_PHOTOS: Array<{ keywords: string[]; url: string }> = [
  // Specific accessories
  {
    keywords: ['cufflink', 'cufflinks', 'clifflinks'],
    url: 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['watch', 'smartwatch', 'chronograph', 'timepiece'],
    url: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['wallet', 'cardholder', 'billfold'],
    url: 'https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['belt', 'leather belt', 'braided belt'],
    url: 'https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tie', 'necktie', 'bow tie', 'pocket square'],
    url: 'https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80',
  },

  // Specific footwear
  {
    keywords: ['loafer', 'loafers', 'penny loafer', 'slip-on', 'moccasin'],
    url: 'https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['oxford', 'brogue', 'brogues', 'derby', 'leather shoe', 'dress shoe'],
    url: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['running', 'sneaker', 'sneakers', 'sports shoe', 'athletic', 'shoe', 'footwear', 'sandal', 'chappal'],
    url: 'https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=600&q=80',
  },

  // Specific blazers and suits
  {
    keywords: ['waistcoat', 'vest'],
    url: 'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['tuxedo', 'tux'],
    url: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['blazer', 'suit', 'jacket', 'nehru'],
    url: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80',
  },

  // Specific dhotis & ethnic wear
  {
    keywords: ['dhoti', 'vesti', 'lungi', 'angavastram', 'veshti', 'ethnic', 'panchakacham', 'kurta', 'sherwani'],
    url: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80',
  },

  // Specific shirts
  {
    keywords: ['linen', 'linen shirt', 'resort', 'mandarin', 'summer shirt', 'casual shirt'],
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['formal shirt', 'office shirt', 'dress shirt', 'oxford shirt', 'poplin', 'twill', 'shirt', 'formal_shirts'],
    url: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80',
  },

  // Specific trousers
  {
    keywords: ['trouser', 'chinos', 'pants', 'formal pants', 'khaki', 'gurkha', 'pleated', 'slacks'],
    url: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80',
  },

  // Polos and tees
  {
    keywords: ['polo', 't-shirt', 'tshirt', 'crewneck', 'tee', 'henley'],
    url: 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80',
  },

  // General accessories fallback
  {
    keywords: ['accessory', 'accessories'],
    url: 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=600&q=80',
  },
];

export const HERO_SHOWCASE_PHOTOS = {
  silkDhoti: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=85',
  blazer: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=85',
  linenShirt: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=85',
  leatherShoes: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=85',
  // Backward-compatible keys
  silkSaree: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=85',
  cookware: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=85',
  filterCoffee: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=85',
  nativeSpices: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=85',
};

export const PROMO_BANNER_PHOTOS = {
  weddingSilks: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=800&q=85',
  summerLinen: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=800&q=85',
  leatherShoes: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=800&q=85',
  // Backward-compatible keys
  handloom: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=800&q=85',
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
  'dhotis_ethnic': 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80',
  'footwear': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
  'accessories': 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=400&q=80',
  'Formal Shirts': 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=400&q=80',
  'Casual Linen': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=400&q=80',
  'Dhotis & Ethnic': 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80',
  'Dhotis & Veshtis': 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80',
  'Trousers & Chinos': 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=400&q=80',
  'Blazers & Suits': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Polos & T-Shirts': 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=400&q=80',
  'Footwear & Loafers': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
  'Accessories': 'https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=400&q=80',
  'mens_wear': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'View All': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  // Backward-compatible aliases
  'Handloom & Silks': 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80',
  'Cookware': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Spices & Masalas': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=400&q=80',
  'Heritage Grains': 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=400&q=80',
  'Filter Coffee': 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=400&q=80',
  'Traditional Sweets': 'https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=400&q=80',
  'Artisan Crafts': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=400&q=80',
};

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
}): string {
  if (product.image_url && product.image_url.startsWith('http')) {
    return product.image_url;
  }

  const searchText = `${product.title || ''} ${product.name_en || ''} ${product.category || ''} ${product.sku || ''}`.toLowerCase();

  for (const item of CURATED_PRODUCT_PHOTOS) {
    if (item.keywords.some((kw) => searchText.includes(kw))) {
      return item.url;
    }
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
