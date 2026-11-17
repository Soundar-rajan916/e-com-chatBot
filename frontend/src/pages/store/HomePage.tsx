import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getBaseUrl, getCategories, getProducts, getStorePolicy } from '../../api/client';
import { CategoryItem, ProductItem, StorePolicy } from '../../api/types';
import { useCart } from '../../context/CartContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';

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
          getProducts({ page_size: 8, in_stock_only: true }).catch(() => ({ items: [], total: 0, page: 1, page_size: 8, total_pages: 0 })),
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

  return (
    <div className="home-page">
      {/* Hero Banner */}
      <section className="home-hero">
        <div className="hero-content">
          <span className="hero-badge">Authentic Regional Selection</span>
          <h1 className="hero-title">Experience the Finest Products of Tamil Nadu</h1>
          <p className="hero-subtitle">
            Traditional Kanchipuram silks, stone cookware, native spices, organic rices, and snacks.
            Delivered straight to your doorstep with guaranteed authenticity.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn-hero-primary">
              Explore Catalog &rarr;
            </Link>
            <Link to="/products?category=Textiles" className="btn-hero-secondary">
              Shop Silk Sarees
            </Link>
          </div>
        </div>
      </section>

      {/* Categories Bar */}
      {categories.length > 0 && (
        <section className="home-categories-section">
          <div className="section-header">
            <h2>Shop by Category</h2>
            <Link to="/products">View All</Link>
          </div>
          <div className="categories-grid">
            {categories.map((cat) => (
              <Link
                key={cat.category}
                to={`/products?category=${encodeURIComponent(cat.category)}`}
                className="category-card"
              >
                <div className="category-icon">{cat.icon || '📦'}</div>
                <span className="category-name">{cat.category.replace(/_/g, ' ')}</span>
                {cat.count !== undefined && (
                  <span className="category-count">({cat.count})</span>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Featured Products */}
      <section className="home-products-section">
        <div className="section-header">
          <h2>Trending &amp; In Demand</h2>
          <Link to="/products">See All 2,000+ Products &rarr;</Link>
        </div>

        {isLoading ? (
          <div className="loading-spinner">Loading featured products...</div>
        ) : (
          <div className="products-grid">
            {(featuredProducts || []).map((p) => {
              const imgUrl = `${getBaseUrl()}/products/${p.id}/image.svg`;
              return (
                <div key={p.id} className="product-card">
                  <Link to={`/products/${p.id}`} className="product-image-container">
                    <img src={imgUrl} alt={p.title} className="product-card-img" />
                    {p.stock <= 5 && <span className="stock-alert-badge">Only {p.stock} left</span>}
                  </Link>

                  <div className="product-card-body">
                    <span className="product-category-tag">{p.category}</span>
                    <Link to={`/products/${p.id}`} className="product-title-link">
                      <h3 className="product-title">{p.title}</h3>
                    </Link>
                    {p.title_ta && <p className="product-tamil-title">{p.title_ta}</p>}

                    <div className="product-pricing">
                      <span className="product-price">₹{Number(p.price_inr).toLocaleString('en-IN')}</span>
                      <span className="product-stock-status">
                        {p.stock > 0 ? 'In Stock' : 'Out of Stock'}
                      </span>
                    </div>

                    <div className="product-card-actions">
                      <button
                        type="button"
                        className="btn-add-cart"
                        onClick={() => void addItem(p.id, 1)}
                        disabled={p.stock <= 0}
                      >
                        Add to Cart
                      </button>
                      <button
                        type="button"
                        className="btn-ask-ai"
                        onClick={() =>
                          askAboutProduct({
                            id: p.id,
                            title: p.title,
                            price_inr: p.price_inr,
                          })
                        }
                        title="Ask our AI assistant about this product in Tamil or English"
                      >
                        Ask AI
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Regional Support Highlight */}
      <section className="home-ai-highlight">
        <div className="ai-highlight-card">
          <div className="ai-highlight-text">
            <h3>Need help in Tamil or English?</h3>
            <p>
              Our regional AI customer support understands Tanglish, Tamil script, and English. Ask
              about order updates, refund conditions, saree fabrics, or cooking guidelines anytime.
            </p>
          </div>
          <div className="ai-highlight-button">
            <Link to="/products" className="btn-ai-explore">
              Start Shopping Now
            </Link>
          </div>
        </div>
      </section>

      {/* Policy Highlights */}
      {policy && (
        <section className="home-policy-banner">
          <div className="policy-pill">
            <span className="policy-icon">🛡️</span>
            <div>
              <strong>7-Day Returns</strong>
              <p>Simple and instant refund policy on eligible items.</p>
            </div>
          </div>
          <div className="policy-pill">
            <span className="policy-icon">🚚</span>
            <div>
              <strong>Cash on Delivery &amp; Demo Cards</strong>
              <p>Flexible checkout options for convenience.</p>
            </div>
          </div>
          <div className="policy-pill">
            <span className="policy-icon">💬</span>
            <div>
              <strong>24x7 Assistant</strong>
              <p>Instant answers and seamless executive escalation.</p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
