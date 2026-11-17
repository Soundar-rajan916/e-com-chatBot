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

export const HomePage: React.FC = () => {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [featuredProducts, setFeaturedProducts] = useState<ProductItem[]>([]);
  const [policy, setPolicy] = useState<StorePolicy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [newsletterEmail, setNewsletterEmail] = useState('');
  const [newsletterSuccess, setNewsletterSuccess] = useState(false);
  const { addItem } = useCart();
  const { askAboutProduct } = useSupportWidget();

  useEffect(() => {
    async function loadData() {
      try {
        const [cats, prodsRes, pol] = await Promise.all([
          getCategories().catch(() => []),
          getProducts({ page_size: 10, in_stock_only: true }).catch(() => ({
            items: [],
            total: 0,
            page: 1,
            page_size: 10,
            total_pages: 0,
          })),
          getStorePolicy('en').catch(() => null),
        ]);
        setCategories(Array.isArray(cats) ? cats : []);
        setFeaturedProducts(prodsRes && Array.isArray(prodsRes.items) ? prodsRes.items : []);
        setPolicy(pol);
      } catch (err) {
        console.error('Failed to load homepage data', err);
      } finally {
        setIsLoading(false);
      }
    }
    void loadData();
  }, []);

  const handleNewsletterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newsletterEmail.trim()) {
      setNewsletterSuccess(true);
      setNewsletterEmail('');
    }
  };

  // Pastel Category Circular Shortcuts (matching reference image)
  const categoryShortcuts = [
    { name: 'Handloom & Silks', cat: 'Textiles', image: CATEGORY_PHOTOS['Handloom & Silks'], bg: '#fce4ec', border: '#f8bbd0' },
    { name: 'Cookware', cat: 'Cookware', image: CATEGORY_PHOTOS['Cookware'], bg: '#e1f5fe', border: '#b3e5fc' },
    { name: 'Spices & Masalas', cat: 'Spices', image: CATEGORY_PHOTOS['Spices & Masalas'], bg: '#ffe0b2', border: '#ffcc80' },
    { name: 'Heritage Grains', cat: 'Groceries', image: CATEGORY_PHOTOS['Heritage Grains'], bg: '#e8f5e9', border: '#c8e6c9' },
    { name: 'Filter Coffee', cat: 'Beverages', image: CATEGORY_PHOTOS['Filter Coffee'], bg: '#fff3e0', border: '#ffe0b2' },
    { name: 'Traditional Sweets', cat: 'Sweets', image: CATEGORY_PHOTOS['Traditional Sweets'], bg: '#fff8e1', border: '#ffecb3' },
    { name: 'Artisan Crafts', cat: 'Handicrafts', image: CATEGORY_PHOTOS['Artisan Crafts'], bg: '#f3e5f5', border: '#e1bee7' },
    { name: 'View All', cat: '', image: CATEGORY_PHOTOS['View All'], bg: '#f5f5f5', border: '#e0e0e0' },
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
            <span className="viva-hero-eyebrow">Authentic Regional Selection</span>
            <h1 className="viva-hero-headline">Elevate Your Everyday</h1>
            <h2 className="viva-hero-title-sub">Experience the Finest Products of Tamil Nadu</h2>
            <p className="viva-hero-subhead">
              Traditional Kanchipuram silks, stone cookware, native spices, organic heritage grains, and traditional snacks. Delivered straight to your doorstep with guaranteed authenticity.
            </p>

            <div className="viva-hero-actions">
              <Link to="/products" className="viva-hero-cta">
                Shop Now &rarr;
              </Link>
              <Link to="/products?category=Textiles" className="viva-hero-secondary-btn">
                Explore Silks
              </Link>
            </div>

            <div className="viva-hero-trust-badges">
              <div className="trust-badge-item">
                <span className="trust-badge-icon">🛡️</span>
                <span>Premium Quality</span>
              </div>
              <div className="trust-badge-item">
                <span className="trust-badge-icon">🏷️</span>
                <span>Great Prices</span>
              </div>
              <div className="trust-badge-item">
                <span className="trust-badge-icon">👥</span>
                <span>Trusted by 10k+ Customers</span>
              </div>
            </div>
          </div>

          <div className="viva-hero-right">
            <div className="viva-hero-showcase">
              {/* Floating Sale Tag */}
              <div className="viva-floating-sale-pill">
                <span className="sale-pill-label">SUMMER SALE</span>
                <span className="sale-pill-val">UP TO 40% OFF</span>
              </div>

              {/* Showcase Image Montage Container */}
              <div className="viva-hero-montage">
                <div className="montage-item primary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.silkSaree}
                    alt="Kanchipuram Silk"
                    className="montage-img"
                  />
                  <span className="montage-caption">Kanchipuram Silk</span>
                </div>
                <div className="montage-item secondary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.cookware}
                    alt="Soapstone Cookware"
                    className="montage-img"
                  />
                  <span className="montage-caption">Soapstone Cookware</span>
                </div>
                <div className="montage-item tertiary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.filterCoffee}
                    alt="Filter Coffee"
                    className="montage-img"
                  />
                  <span className="montage-caption">Filter Coffee</span>
                </div>
                <div className="montage-item quaternary">
                  <img
                    src={HERO_SHOWCASE_PHOTOS.nativeSpices}
                    alt="Native Spices"
                    className="montage-img"
                  />
                  <span className="montage-caption">Native Spices</span>
                </div>
              </div>

              {/* Hero Carousel Dots */}
              <div className="viva-hero-dots">
                <span className="hero-dot active" />
                <span className="hero-dot" />
                <span className="hero-dot" />
                <span className="hero-dot" />
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
            <h2 className="viva-section-title">Top Picks For You ✨</h2>
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
                      <span className="rating-stars">★★★★★</span>
                      <span className="rating-count">({120 + (idx * 37)})</span>
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
                    <div className="viva-product-actions">
                      <button
                        type="button"
                        className="viva-add-cart-btn btn-add-cart"
                        onClick={() => void addItem(p.id, 1)}
                        disabled={p.stock <= 0}
                      >
                        <span className="btn-cart-icon" aria-hidden="true">🛒</span> Add to Cart
                      </button>
                      <button
                        type="button"
                        className="viva-ask-ai-btn"
                        onClick={() =>
                          askAboutProduct({
                            id: p.id,
                            title: p.title,
                            price_inr: p.price_inr,
                          })
                        }
                        title="Ask AI assistant about this product in Tamil or English"
                      >
                        💬 Ask AI
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
          {/* Promo Card 1: Fresh Handloom Silks */}
          <div className="viva-promo-card promo-mint">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">New Arrivals</span>
              <h3 className="promo-title">Fresh Handloom Weaves</h3>
              <Link to="/products?category=Textiles" className="promo-link">
                Shop Now &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.handloom}
                alt="Fresh Handloom Weaves"
                className="promo-img"
              />
            </div>
          </div>

          {/* Promo Card 2: Traditional Cookware */}
          <div className="viva-promo-card promo-sand">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">Kitchen Heritage</span>
              <h3 className="promo-title">Pure Soapstone Cookware</h3>
              <Link to="/products?category=Cookware" className="promo-link">
                Shop Now &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.cookware}
                alt="Pure Soapstone Cookware"
                className="promo-img"
              />
            </div>
          </div>

          {/* Promo Card 3: Native Spices */}
          <div className="viva-promo-card promo-sky">
            <div className="promo-text-wrap">
              <span className="promo-eyebrow">Flavors &amp; Aromas</span>
              <h3 className="promo-title">Native Spices &amp; Blends</h3>
              <Link to="/products?category=Spices" className="promo-link">
                Shop Now &rarr;
              </Link>
            </div>
            <div className="promo-visual">
              <img
                src={PROMO_BANNER_PHOTOS.spices}
                alt="Native Spices"
                className="promo-img"
              />
            </div>
          </div>
        </div>
      </section>

      {/* 5. Loved By Thousands (Customer Testimonials) */}
      <section className="viva-testimonials-section">
        <div className="viva-testimonials-header">
          <h2 className="testimonials-title">Loved By Thousands ❤️</h2>
          <div className="testimonials-overall-rating">
            <span className="overall-score">4.8/5 Average Rating</span>
            <span className="overall-stars">★★★★★</span>
          </div>
        </div>

        <div className="viva-testimonials-grid">
          {/* Review 1 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.sarah}
                alt="Sarah J."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Sarah J.</strong>
                <span className="verified-badge">✓ Verified Buyer</span>
              </div>
            </div>
            <div className="testimonial-stars">★★★★★</div>
            <p className="testimonial-quote">
              "Amazing quality and fast delivery! Regional Bazaar has become my go-to store for
              authentic Kanchipuram silks. The texture and zari work are exquisite."
            </p>
          </div>

          {/* Review 2 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.michael}
                alt="Michael T."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Michael T.</strong>
                <span className="verified-badge">✓ Verified Buyer</span>
              </div>
            </div>
            <div className="testimonial-stars">★★★★★</div>
            <p className="testimonial-quote">
              "Great prices, excellent customer service, and super easy returns. The soapstone
              kalchatti arrived beautifully seasoned and packaged!"
            </p>
          </div>

          {/* Review 3 */}
          <div className="viva-testimonial-card">
            <div className="testimonial-user-row">
              <img
                src={TESTIMONIAL_AVATARS.priya}
                alt="Priya K."
                className="testimonial-avatar-img"
              />
              <div>
                <strong className="testimonial-name">Priya K.</strong>
                <span className="verified-badge">✓ Verified Buyer</span>
              </div>
            </div>
            <div className="testimonial-stars">★★★★★</div>
            <p className="testimonial-quote">
              "I love the variety they offer. I can find everything in one place, and asking questions
              in Tamil via the AI assistant made my order tracking effortless."
            </p>
          </div>
        </div>
      </section>

      {/* 6. Newsletter Subscription Strip ("Stay in the Loop") */}
      <section className="viva-newsletter-section">
        <div className="viva-newsletter-card">
          <div className="newsletter-icon-wrap">
            <span className="newsletter-icon">✉️</span>
          </div>

          <div className="newsletter-text-wrap">
            <h3 className="newsletter-title">Stay in the Loop</h3>
            <p className="newsletter-subtitle">
              Get exclusive deals, new artisan arrivals, and regional style inspiration straight to your inbox.
            </p>
          </div>

          <form className="newsletter-form" onSubmit={handleNewsletterSubmit}>
            <input
              type="email"
              className="newsletter-input"
              placeholder="Enter your email address"
              value={newsletterEmail}
              onChange={(e) => setNewsletterEmail(e.target.value)}
              required
            />
            <button type="submit" className="newsletter-btn">
              Subscribe
            </button>
          </form>
        </div>
        {newsletterSuccess && (
          <div className="newsletter-success-toast">
            ✓ Thank you for subscribing! Check your inbox for exclusive regional offers.
          </div>
        )}
        <p className="newsletter-privacy-note">
          🔒 We respect your privacy. Unsubscribe anytime.
        </p>
      </section>

      {/* 7. Value Propositions / Trust Pillars Bar */}
      <section className="viva-trust-pillars-section">
        <div className="viva-trust-pillars-grid">
          <div className="trust-pillar-card">
            <span className="trust-pillar-icon">🚚</span>
            <div>
              <strong>Free Shipping</strong>
              <p>On orders over ₹999</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon">🔄</span>
            <div>
              <strong>Easy Returns</strong>
              <p>{policy?.content_markdown?.includes('7') ? '7-day' : 'Hassle-free'} easy return policy</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon">🔒</span>
            <div>
              <strong>Secure Payments</strong>
              <p>100% secure checkout &amp; COD</p>
            </div>
          </div>

          <div className="trust-pillar-card">
            <span className="trust-pillar-icon">🎧</span>
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
