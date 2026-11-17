import { getBaseUrl } from '../api/client';

// Curated high-resolution lifestyle product photos for key catalog types (Men's Wear focus)
const CURATED_PRODUCT_PHOTOS: Array<{ keywords: string[]; url: string }> = [
  {
    keywords: ['dhoti', 'vesti', 'lungi', 'angavastram', 'veshti'],
    url: '/images/hero/dhoti.svg',
  },
  {
    keywords: ['blazer', 'suit', 'jacket', 'tuxedo'],
    url: '/images/hero/blazer.svg',
  },
  {
    keywords: ['linen', 'linen shirt', 'casual shirt', 'cotton shirt'],
    url: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['formal shirt', 'office shirt', 'dress shirt', 'oxford shirt'],
    url: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['trouser', 'chinos', 'pants', 'formal pants', 'khaki'],
    url: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['polo', 't-shirt', 'tshirt', 'crewneck', 'tee'],
    url: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['shoe', 'oxford', 'leather', 'loafers', 'brogues', 'footwear', 'chappals', 'sandals', 'running'],
    url: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['belt', 'wallet', 'watch', 'tie', 'cufflink', 'accessory'],
    url: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['kurti', 'kurta', 'silk', 'kanchipuram', 'ethnic'],
    url: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['headphone', 'wireless', 'audio'],
    url: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
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
  'Formal Shirts': '/images/categories/formal_shirts.svg',
  'Casual Linen': '/images/categories/linen.svg',
  'Dhotis & Veshtis': '/images/categories/dhotis.svg',
  'Trousers & Chinos': '/images/categories/trousers.svg',
  'Blazers & Suits': '/images/categories/blazers.svg',
  'Polos & T-Shirts': '/images/categories/polos.svg',
  'Footwear & Loafers': '/images/categories/footwear.svg',
  'Accessories': '/images/categories/accessories.svg',
  // Backward-compatible aliases
  'Handloom & Silks': '/images/categories/dhotis.svg',
  'Cookware': '/images/categories/formal_shirts.svg',
  'Spices & Masalas': '/images/categories/linen.svg',
  'Heritage Grains': '/images/categories/trousers.svg',
  'Filter Coffee': '/images/categories/blazers.svg',
  'Traditional Sweets': '/images/categories/polos.svg',
  'Artisan Crafts': '/images/categories/footwear.svg',
  'View All': '/images/categories/all.svg',
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
