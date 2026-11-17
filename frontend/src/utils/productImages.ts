import { getBaseUrl } from '../api/client';

// Curated high-resolution lifestyle product photos for key catalog types
const CURATED_PRODUCT_PHOTOS: Array<{ keywords: string[]; url: string }> = [
  {
    keywords: ['headphone', 'wireless', 'earphone', 'audio', 'sound'],
    url: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['kurti', 'saree', 'silk', 'kanchipuram', 'textile', 'clothing', 'dupatta', 'dress'],
    url: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['shirt', 'linen', 'mens', 't-shirt', 'casual'],
    url: 'https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['kalchatti', 'cookware', 'kadai', 'stone pot', 'kitchenware', 'vessel', 'pressure cooker'],
    url: 'https://images.unsplash.com/photo-1584990347449-389f41b37d40?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['mug', 'ceramic', 'cup', 'coffee mug'],
    url: 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['shoe', 'running', 'footwear', 'sneaker', 'sandals', 'chappals', 'loafers'],
    url: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['spice', 'masala', 'pepper', 'cardamom', 'turmeric', 'chili'],
    url: 'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['grain', 'rice', 'groceries', 'millet', 'dhal', 'wheat'],
    url: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['coffee', 'filter coffee', 'beverage', 'tea', 'roast'],
    url: 'https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['serum', 'skincare', 'beauty', 'lotion', 'oil', 'cream'],
    url: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['backpack', 'bag', 'travel', 'duffel'],
    url: 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['sweet', 'laddu', 'halwa', 'snack', 'candy'],
    url: 'https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['craft', 'brass', 'handicraft', 'terracotta', 'idol', 'pottery'],
    url: 'https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=600&q=80',
  },
  {
    keywords: ['watch', 'smartwatch', 'band'],
    url: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80',
  },
];

export const HERO_SHOWCASE_PHOTOS = {
  silkSaree: '/images/hero/saree.svg',
  cookware: '/images/hero/cookware.svg',
  filterCoffee: '/images/hero/coffee.svg',
  nativeSpices: '/images/hero/spices.svg',
};

export const PROMO_BANNER_PHOTOS = {
  handloom: '/images/promos/handloom.svg',
  cookware: '/images/promos/cookware.svg',
  spices: '/images/promos/spices.svg',
};

export const TESTIMONIAL_AVATARS = {
  sarah: '/images/testimonials/sarah.svg',
  michael: '/images/testimonials/michael.svg',
  priya: '/images/testimonials/priya.svg',
};

export const CATEGORY_PHOTOS: Record<string, string> = {
  'Handloom & Silks': '/images/categories/textiles.svg',
  'Cookware': '/images/categories/cookware.svg',
  'Spices & Masalas': '/images/categories/spices.svg',
  'Heritage Grains': '/images/categories/groceries.svg',
  'Filter Coffee': '/images/categories/coffee.svg',
  'Traditional Sweets': '/images/categories/sweets.svg',
  'Artisan Crafts': '/images/categories/crafts.svg',
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

  return 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=600&q=80';
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
    : '/images/categories/all.svg';

  if (target.src !== fallbackUrl && !target.src.endsWith(fallbackUrl)) {
    target.src = fallbackUrl;
  }
}
