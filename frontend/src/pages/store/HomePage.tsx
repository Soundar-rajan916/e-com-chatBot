import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCategories, getProducts, getStorePolicy } from '../../api/client';
import { CategoryItem, ProductItem, StorePolicy } from '../../api/types';
import { useCart } from '../../context/CartContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';
import {
  CATEGORY_PHOTOS,
  HERO_SHOWCASE_PHOTOS,
  PROMO_BANNER_PHOTOS,
  TESTIMONIAL_AVATARS,
  getProductImageUrl,
  handleProductImageError,
} from '../../utils/productImages';
import {
  ShieldCheckIcon,
  TagIcon,
  UsersIcon,
  BagIcon,
  ChatIcon,
  StarRating,
  CheckIcon,
  LockIcon,
  TruckIcon,
  RotateCcwIcon,
  HeadphonesIcon,
} from '../../components/icons';

export const HomePage: React.FC = () => {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [featuredProducts, setFeaturedProducts] = useState<ProductItem[]>([]);
  const [policy, setPolicy] = useState<StorePolicy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { addItem } = useCart();
  const { askAboutProduct } = useSupportWidget();

  useEffect(() => {
    async function loadData() {
      try {
        const [cats, prodsRes, pol] = await Promise.all([
          getCategories().catch(() => []),
          getProducts({ page_size: 20, in_stock_only: true }).catch(() => ({
            items: [],
            total: 0,
            page: 1,
            page_size: 20,
            total_pages: 0,
          })),
          getStorePolicy('en').catch(() => null),
        ]);
        setCategories(Array.isArray(cats) ? cats : []);
        // Store is 100% exclusive Men's Wear
        const allItems = prodsRes && Array.isArray(prodsRes.items) ? prodsRes.items : [];
        setFeaturedProducts(allItems);
        setPolicy(pol);
      } catch (err) {
        console.error('Failed to load homepage data', err);
      } finally {
        setIsLoading(false);
      }
    }
    void loadData();
  }, []);

  // Dedicated Men's Wear Category Shortcuts
  const categoryShortcuts = [
    { name: 'Formal Shirts', cat: 'formal_shirts', image: CATEGORY_PHOTOS['formal_shirts'], bg: '#e0f2fe', border: '#bae6fd' },
    { name: 'Casual Linen', cat: 'casual_shirts', image: CATEGORY_PHOTOS['casual_shirts'], bg: '#f0fdf4', border: '#bbf7d0' },
    { name: 'Dhotis & Ethnic', cat: 'dhotis_ethnic', image: CATEGORY_PHOTOS['dhotis_ethnic'], bg: '#fffbeb', border: '#fef08a' },
    { name: 'Trousers & Chinos', cat: 'trousers_chinos', image: CATEGORY_PHOTOS['trousers_chinos'], bg: '#f8fafc', border: '#e2e8f0' },
    { name: 'Blazers & Suits', cat: 'blazers_suits', image: CATEGORY_PHOTOS['blazers_suits'], bg: '#f1f5f9', border: '#cbd5e1' },
    { name: 'Polos & T-Shirts', cat: 'tshirts_polos', image: CATEGORY_PHOTOS['tshirts_polos'], bg: '#fef2f2', border: '#fecaca' },
    { name: 'Footwear & Loafers', cat: 'footwear', image: CATEGORY_PHOTOS['footwear'], bg: '#fff7ed', border: '#fed7aa' },
    { name: 'Accessories', cat: 'accessories', image: CATEGORY_PHOTOS['accessories'], bg: '#f5f3ff', border: '#ddd6fe' },
    { name: 'View All', cat: '', image: CATEGORY_PHOTOS['View All'], bg: '#f1f5f9', border: '#cbd5e1' },
  ].map((item) => {
    const found = categories.find((c) => c.category.toLowerCase() === item.cat.toLowerCase());
    return { ...item, count: found?.count };
  });

  return (
    <div className="home-page">
      {/* 1. Curved Hero Banner */}
      <section className="viva-hero-section">
        <div className="viva-hero-card">
          <div className="viva-hero-left">
            <span className="viva-hero-eyebrow">Refined Men's Apparel &amp; Traditional Wear</span>
            <h1 className="viva-hero-headline">Elevate Your Everyday Style</h1>
            <h2 className="viva-hero-title-sub">Experience the Finest Products of Tamil Nadu</h2>
            <p className="viva-hero-subhead">
              Tailored linen shirts, pure Kanchipuram silk wedding dhotis, bespoke festive blazers, formal trousers, and handcrafted leather footwear. Delivered with guaranteed authenticity and precision fit.
            </p>

            <div className="viva-hero-actions">
              <Link to="/products" className="viva-hero-cta">
                Shop Men's Wear &rarr;
              </Link>
              <Link to="/products?category=dhotis_ethnic" className="viva-hero-secondary-btn">
                Explore Dhotis
              </Link>
            </div>

            <div className="viva-hero-trust-badges">
              <div className="trust-badge-item">
                <span className="trust-badge-icon"><ShieldCheckIcon size={16} /></span>
                <span>Premium Quality</span>
              </div>
              <div className="trust-badge-item">
                <span className="trust-badge-icon"><TagIcon size={16} /></span>
                <span>Great Prices</span>
              </div>
              <div className="trust-badge-item">
                <span className="trust-badge-icon"><UsersIcon size={16} /></span>
                <span>Trusted by 10k+ Customers</span>
              </div>
            </div>
          </div>

          <div className="viva-hero-right">
            <div className="viva-hero-showcase">
              {/* Floating Sale Tag */}
              <div className="viva-floating-sale-pill">
                <span className="sale-pill-label">SUMMER EDIT</span>
                <span className="sale-pill-val">UP TO 40% OFF</span>
              </div>

              {/* Showcase Image Montage Container */}
              <div className="viva-hero-montage">
                <Link to="/products?category=dhotis_ethnic" className="montage-item primary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.silkDhoti}
                    alt="Silk Dhoti & Kurta"
                    className="montage-img"
                  />
                  <span className="montage-caption">Silk Dhoti &amp; Kurta</span>
                </Link>
                <Link to="/products?category=blazers_suits" className="montage-item secondary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.blazer}
                    alt="Tailored Blazer"
                    className="montage-img"
                  />
                  <span className="montage-caption">Tailored Blazer</span>
                </Link>
                <Link to="/products?category=casual_shirts" className="montage-item tertiary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.linenShirt}
                    alt="Pure Linen Shirt"
                    className="montage-img"
                  />
                  <span className="montage-caption">Pure Linen Shirt</span>
                </Link>
                <Link to="/products?category=footwear" className="montage-item quaternary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.leatherShoes}
                    alt="Leather Loafers"
                    className="montage-img"
                  />
                  <span className="montage-caption">Leather Loafers</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Circular Pastel Category Badges */}
      <section className="viva-category-circles-section">
        <div className="viva-category-circles-container">
          {categoryShortcuts.map((c, idx) => (
            <Link
              key={idx}
              to={c.cat ? `/products?category=${encodeURIComponent(c.cat)}` : '/products'}
              className="category-circle-item"
            >
              <div
                className="category-circle-avatar"
                style={{ backgroundColor: c.bg, borderColor: c.border }}
              >
                <img
                  src={c.image}
                  alt={c.name}
                  className="category-circle-img"
                  loading="lazy"
                />
              </div>
              <span className="category-circle-name">{c.name}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* 3. Top Picks For You (Products Grid) */}
      <section className="viva-products-section">
        <div className="viva-section-header">
          <div className="section-title-wrap">
            <h2 className="viva-section-title">Top Picks For You</h2>
            <p className="viva-section-subtitle">
              Handcrafted, ethically sourced, and curated for authentic quality.
            </p>
          </div>
          <Link to="/products" className="viva-see-all-link">
            See All Deals &rarr;
          </Link>
        </div>

        {isLoading ? (
          <div className="viva-loading-state">
            <div className="viva-spinner" />
            <p>Loading curated products...</p>
          </div>
        ) : (
          <div className="viva-products-grid">
            {(featuredProducts || []).slice(0, 8).map((p, idx) => {
              const imgUrl = getProductImageUrl(p);
              const discountPercent = idx % 2 === 0 ? '-20%' : '-15%';
              const originalPrice = Math.round(Number(p.price_inr) * 1.25);

              return (
                <div key={p.id} className="viva-product-card">
                  {/* Discount Tag */}
                  <span className="viva-discount-tag">{discountPercent}</span>

                  {/* Product Image Link */}
                  <Link to={`/products/${p.id}`} className="viva-product-image-wrap">
                    <img
                      src={imgUrl}
                      alt={p.title}
                      className="viva-product-img"
                      onError={(e) => handleProductImageError(e, p.id)}
                    />
                    {p.stock <= 5 && (
                      <span className="viva-stock-tag">Only {p.stock} left</span>
                    )}
                  </Link>

                  {/* Product Details */}
                  <div className="viva-product-info">
                    <Link to={`/products/${p.id}`} className="viva-product-title-link">
                      <h3 className="viva-product-title">{p.title}</h3>
                    </Link>
                    {p.title_ta && <p className="viva-product-tamil">{p.title_ta}</p>}

                    {/* Star Rating */}
                    <div className="viva-product-rating">
                      <StarRating count={5} size={13} />
                      <span className="rating-count" style={{ marginLeft: '6px' }}>({120 + (idx * 37)})</span>
                    </div>

                    {/* Pricing */}
                    <div className="viva-product-pricing">
                      <span className="viva-price-current">
                        ₹{Number(p.price_inr).toLocaleString('en-IN')}
                      </span>
                      <span className="viva-price-original">
                        ₹{originalPrice.toLocaleString('en-IN')}
                      </span>
                    </div>

                    {/* Quick Action Buttons */}
                    <div className="viva-product-actions product-card-actions">
                      <button
                        type="button"
                        className="viva-add-cart-btn btn-add-cart"
                        onClick={() => void addItem(p.id, 1)}
                        disabled={p.stock <= 0}
                      >
                        <BagIcon size={14} />
                        <span>{p.stock > 0 ? 'Add to Cart' : 'Sold Out'}</span>
                      </button>
                      <button
                        type="button"
                        className="viva-ask-ai-btn btn-ask-ai"
                        onClick={() =>
                          askAboutProduct({
                            id: p.id,
                            title: p.title,
                            price_inr: p.price_inr,
                          })
                        }
                        title="Ask AI assistant about this product in Tamil or English"
                        aria-label="Ask AI about this product"
                      >
                        <ChatIcon size={14} />
                        <span>Ask AI</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 4. Three Curated Lifestyle Promo Cards */}
      <section className="viva-promo-banners-section">
        <div className="viva-promo-grid">
          {/* Promo Card 1: Wedding & Festive Silks */}
          <div className="viva-promo-card promo-mint">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">Wedding &amp; Festive</span>
              <h3 className="promo-title">Pure Silk Dhotis &amp; Kurtas</h3>
              <Link to="/products?category=dhotis_ethnic" className="promo-link">
                Shop Dhotis &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.weddingSilks}
                alt="Pure Silk Dhotis &amp; Kurtas"
                className="promo-img"
              />
            </div>
          </div>

          {/* Promo Card 2: Summer Linen Collection */}
          <div className="viva-promo-card promo-sand">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">Summer Essentials</span>
              <h3 className="promo-title">100% Breathable Linen Shirts</h3>
              <Link to="/products?category=casual_shirts" className="promo-link">
                Shop Linen &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.summerLinen}
                alt="100% Breathable Linen Shirts"
                className="promo-img"
              />
            </div>
          </div>

          {/* Promo Card 3: Handcrafted Leather Footwear */}
          <div className="viva-promo-card promo-sky">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">Artisanal Craft</span>
              <h3 className="promo-title">Handcrafted Leather Footwear</h3>
              <Link to="/products?category=footwear" className="promo-link">
                Shop Footwear &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.leatherShoes}
                alt="Handcrafted Leather Footwear"
                className="promo-img"
              />
            </div>
          </div>
        </div>
      </section>

      {/* 5. Loved By Thousands (Customer Testimonials) */}
      <section className="viva-testimonials-section">
        <div className="viva-testimonials-header">
          <h2 className="testimonials-title">Loved By Thousands</h2>
          <div className="testimonials-overall-rating" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <span className="overall-score">4.8/5 Average Rating</span>
            <StarRating count={5} size={14} />
          </div>
        </div>

        <div className="viva-testimonials-grid">
          {/* Review 1 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.karthik}
                alt="Karthik R."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Karthik R.</strong>
                <span className="verified-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <CheckIcon size={12} /> Verified Buyer
                </span>
              </div>
            </div>
            <div className="testimonial-stars" style={{ margin: '8px 0' }}>
              <StarRating count={5} size={13} />
            </div>
            <p className="testimonial-quote">
              "The pure silk dhoti set for my wedding was breathtaking. Exquisite zari border, perfect traditional drape, and fast delivery!"
            </p>
          </div>

          {/* Review 2 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.arvind}
                alt="Arvind S."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Arvind S.</strong>
                <span className="verified-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <CheckIcon size={12} /> Verified Buyer
                </span>
              </div>
            </div>
            <div className="testimonial-stars" style={{ margin: '8px 0' }}>
              <StarRating count={5} size={13} />
            </div>
            <p className="testimonial-quote">
              "Crisp collar structure, wrinkle-resistant cotton, and breathable linen. Easily the best formal and casual shirts I've ordered online."
            </p>
          </div>

          {/* Review 3 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.michael}
                alt="Michael T."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Michael T.</strong>
                <span className="verified-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <CheckIcon size={12} /> Verified Buyer
                </span>
              </div>
            </div>
            <div className="testimonial-stars" style={{ margin: '8px 0' }}>
              <StarRating count={5} size={13} />
            </div>
            <p className="testimonial-quote">
              "Superb tailoring on the blazers and chinos. Sizing was spot-on, and the AI assistant recommended the exact right sleeve and collar size!"
            </p>
          </div>
        </div>
      </section>

      {/* 6. Value Propositions / Trust Pillars Bar */}
      <section className="viva-trust-pillars-section">
        <div className="viva-trust-pillars-grid">
          <div className="trust-pillar-card">
            <span className="trust-pillar-icon"><TruckIcon size={20} /></span>
            <div>
              <strong>Free Shipping</strong>
              <p>On orders over ₹999</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon"><RotateCcwIcon size={20} /></span>
            <div>
              <strong>Easy Returns</strong>
              <p>{policy?.content_markdown?.includes('7') ? '7-day' : 'Hassle-free'} easy return policy</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon"><LockIcon size={20} /></span>
            <div>
              <strong>Secure Payments</strong>
              <p>100% secure checkout &amp; COD</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon"><HeadphonesIcon size={20} /></span>
            <div>
              <strong>24/7 Support</strong>
              <p>AI assistance in English &amp; தமிழ்</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
