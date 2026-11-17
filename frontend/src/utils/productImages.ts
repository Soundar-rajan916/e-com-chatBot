import { getBaseUrl } from '../api/client';

// Curated high-resolution lifestyle product photos for key catalog types (100% Men's Wear focus)
const CURATED_PRODUCT_PHOTOS: Array<{ keywords: string[]; url: string }> = [
  {
    keywords: ['dhoti', 'vesti', 'lungi', 'angavastram', 'veshti', 'ethnic', 'panchakacham'],
    url: '/images/hero/dhoti.svg',
  },
  {
    keywords: ['blazer', 'suit', 'jacket', 'tuxedo', 'waistcoat', 'nehru'],
    url: '/images/hero/blazer.svg',
  },
  {
    keywords: ['linen', 'linen shirt', 'casual shirt', 'mandarin', 'chambray', 'resort'],
    url: '/images/hero/shirt.svg',
  },
  {
    keywords: ['formal shirt', 'office shirt', 'dress shirt', 'oxford shirt', 'poplin', 'twill'],
    url: '/images/categories/formal_shirts.svg',
  },
  {
    keywords: ['trouser', 'chinos', 'pants', 'formal pants', 'khaki', 'gurkha', 'pleated'],
    url: '/images/hero/trousers.svg',
  },
  {
    keywords: ['polo', 't-shirt', 'tshirt', 'crewneck', 'tee', 'henley'],
    url: '/images/hero/polo.svg',
  },
  {
    keywords: ['shoe', 'oxford', 'leather', 'loafers', 'brogues', 'footwear', 'chappals', 'sandals', 'running', 'moccasin'],
    url: '/images/hero/shoes.svg',
  },
  {
    keywords: ['belt', 'wallet', 'watch', 'tie', 'cufflink', 'accessory', 'cardholder', 'pocket square'],
    url: '/images/hero/accessories.svg',
  },
];

export const HERO_SHOWCASE_PHOTOS = {
  silkDhoti: '/images/hero/dhoti.svg',
  blazer: '/images/hero/blazer.svg',
  linenShirt: '/images/hero/shirt.svg',
  leatherShoes: '/images/hero/shoes.svg',
  // Backward-compatible keys
  silkSaree: '/images/hero/dhoti.svg',
  cookware: '/images/hero/blazer.svg',
  filterCoffee: '/images/hero/shirt.svg',
  nativeSpices: '/images/hero/shoes.svg',
};

export const PROMO_BANNER_PHOTOS = {
  weddingSilks: '/images/promos/wedding_silks.svg',
  summerLinen: '/images/promos/summer_linen.svg',
  leatherShoes: '/images/promos/leather_shoes.svg',
  // Backward-compatible keys
  handloom: '/images/promos/wedding_silks.svg',
  cookware: '/images/promos/summer_linen.svg',
  spices: '/images/promos/leather_shoes.svg',
};

export const TESTIMONIAL_AVATARS = {
  karthik: '/images/testimonials/karthik.svg',
  arvind: '/images/testimonials/arvind.svg',
  michael: '/images/testimonials/michael.svg',
  // Backward-compatible keys
  sarah: '/images/testimonials/karthik.svg',
  priya: '/images/testimonials/arvind.svg',
};

export const CATEGORY_PHOTOS: Record<string, string> = {
  'formal_shirts': '/images/categories/formal_shirts.svg',
  'casual_shirts': '/images/categories/linen.svg',
  'tshirts_polos': '/images/categories/polos.svg',
  'trousers_chinos': '/images/categories/trousers.svg',
  'blazers_suits': '/images/categories/blazers.svg',
  'dhotis_ethnic': '/images/categories/dhotis.svg',
  'footwear': '/images/categories/footwear.svg',
  'accessories': '/images/categories/accessories.svg',
  'Formal Shirts': '/images/categories/formal_shirts.svg',
  'Casual Linen': '/images/categories/linen.svg',
  'Dhotis & Ethnic': '/images/categories/dhotis.svg',
  'Dhotis & Veshtis': '/images/categories/dhotis.svg',
  'Trousers & Chinos': '/images/categories/trousers.svg',
  'Blazers & Suits': '/images/categories/blazers.svg',
  'Polos & T-Shirts': '/images/categories/polos.svg',
  'Footwear & Loafers': '/images/categories/footwear.svg',
  'Accessories': '/images/categories/accessories.svg',
  'mens_wear': '/images/categories/formal_shirts.svg',
  'View All': '/images/categories/all.svg',
  // Backward-compatible aliases
  'Handloom & Silks': '/images/categories/dhotis.svg',
  'Cookware': '/images/categories/formal_shirts.svg',
  'Spices & Masalas': '/images/categories/linen.svg',
  'Heritage Grains': '/images/categories/trousers.svg',
  'Filter Coffee': '/images/categories/blazers.svg',
  'Traditional Sweets': '/images/categories/polos.svg',
  'Artisan Crafts': '/images/categories/footwear.svg',
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
