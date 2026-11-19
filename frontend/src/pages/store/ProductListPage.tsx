import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getCategories, getProducts } from '../../api/client';
import { CategoryItem, ProductItem } from '../../api/types';
import { useCart } from '../../context/CartContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';
import { getProductImageUrl, handleProductImageError } from '../../utils/productImages';
import { BagIcon, ChatIcon } from '../../components/icons';

const formatCategoryTitle = (catKey: string): string => {
  const map: Record<string, string> = {
    formal_shirts: 'Formal Shirts',
    casual_shirts: 'Casual & Linen',
    tshirts_polos: 'Polos & T-Shirts',
    trousers_chinos: 'Trousers & Chinos',
    blazers_suits: 'Blazers & Suits',
    dhotis_ethnic: 'Dhotis & Ethnic',
    footwear: 'Footwear & Loafers',
    accessories: 'Leather & Accessories',
  };
  return map[catKey] || catKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

export const ProductListPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const query = searchParams.get('q') || '';
  const category = searchParams.get('category') || '';
  const sort = searchParams.get('sort') || '';
  const page = parseInt(searchParams.get('page') || '1', 10);
  const inStockOnly = searchParams.get('in_stock') === 'true';

  const { addItem } = useCart();
  const { askAboutProduct } = useSupportWidget();

  useEffect(() => {
    void getCategories()
      .then((cats) => setCategories(Array.isArray(cats) ? cats : []))
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    async function fetchProducts() {
      setIsLoading(true);
      try {
        const res = await getProducts({
          q: query || undefined,
          category: category || undefined,
          sort: sort || undefined,
          in_stock_only: inStockOnly || undefined,
          page,
          page_size: 16,
        });
        setProducts(Array.isArray(res?.items) ? res.items : []);
        setTotalCount(res?.total || 0);
        setTotalPages(res?.total_pages || 1);
      } catch (err) {
        console.error('Failed to load products', err);
        setProducts([]);
      } finally {
        setIsLoading(false);
      }
    }
    void fetchProducts();
  }, [query, category, sort, page, inStockOnly]);

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set('page', '1'); // reset page on filter change
    setSearchParams(next);
  };

  const handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const searchVal = formData.get('search') as string;
    updateParam('q', searchVal.trim());
  };

  return (
    <div className="catalog-page">
      {/* Editorial Collection Banner matching Wink reference */}
      <section className="wink-catalog-banner" aria-label="Featured Collection Banner">
        <div className="wink-banner-media">
          <img
            src="https://images.unsplash.com/photo-1558769132-cb1aea458c5e?auto=format&fit=crop&w=1200&q=80"
            alt="Explore The Various Collection of Regional Bazaar"
            className="wink-banner-img"
            onError={(e) => {
              e.currentTarget.src = 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=1200&q=80';
            }}
          />
        </div>
        <div className="wink-banner-content">
          <span className="wink-banner-eyebrow">- Collections</span>
          <h2 className="wink-banner-title">
            Explore The Various Collection of {category ? formatCategoryTitle(category) : 'Regional Bazaar'}
          </h2>
          <p className="wink-banner-subtitle">
            Don't miss out to shopping collection from us! you'll not be let down.
          </p>
        </div>
      </section>

      <nav aria-label="Breadcrumb" className="wink-breadcrumb">
        <Link to="/">Home</Link>
        <span className="wink-breadcrumb-sep">&gt;</span>
        <span className="wink-breadcrumb-current">
          {category ? formatCategoryTitle(category) : 'Regional Bazaar Collection'}
        </span>
      </nav>

      <div className="catalog-header">
        <h1>{category ? formatCategoryTitle(category) : 'Regional Bazaar Collection'}</h1>
        <p className="catalog-count-note">
          Showing {products.length} of {totalCount} authentic products
        </p>
      </div>

      <div className="catalog-layout">
        {/* Filter Sidebar */}
        <aside className="catalog-sidebar">
          <div className="filter-group">
            <h3>Search</h3>
            <form onSubmit={handleSearchSubmit} className="search-form">
              <input
                type="text"
                name="search"
                defaultValue={query}
                placeholder="Search formal shirts, linen, dhotis, blazers, footwear..."
                className="filter-search-input"
              />
              <button type="submit" className="btn-filter-search">
                Search
              </button>
            </form>
          </div>

          <div className="filter-group">
            <h3>Category</h3>
            <div className="filter-options-list">
              <button
                type="button"
                className={`filter-option-btn ${!category ? 'active' : ''}`}
                onClick={() => updateParam('category', '')}
              >
                All Categories
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.category}
                  type="button"
                  className={`filter-option-btn ${category === cat.category ? 'active' : ''}`}
                  onClick={() => updateParam('category', cat.category)}
                >
                  {formatCategoryTitle(cat.category)}
                  {cat.count !== undefined ? ` (${cat.count})` : ''}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <h3>Sort By</h3>
            <select
              value={sort}
              onChange={(e) => updateParam('sort', e.target.value)}
              className="filter-select"
            >
              <option value="">Featured</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="title_asc">Title: A to Z</option>
            </select>
          </div>

          <div className="filter-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(e) => updateParam('in_stock', e.target.checked ? 'true' : '')}
              />
              In Stock Only
            </label>
          </div>

          {(query || category || sort || inStockOnly) && (
            <button
              type="button"
              className="btn-clear-filters"
              onClick={() => setSearchParams(new URLSearchParams())}
            >
              Clear All Filters
            </button>
          )}
        </aside>

        {/* Product Grid */}
        <main className="catalog-main">
          {isLoading ? (
            <div className="loading-spinner">Loading catalog...</div>
          ) : products.length === 0 ? (
            <div className="empty-catalog-notice">
              <h3>No products found</h3>
              <p>Try refining your search terms or clearing selected category filters.</p>
              <button
                type="button"
                className="btn-clear-filters"
                onClick={() => setSearchParams(new URLSearchParams())}
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <>
              <div className="products-grid">
                {products.map((p) => {
                  const imgUrl = getProductImageUrl(p);
                  return (
                    <div key={p.id} className={`product-card ${p.stock <= 0 ? 'out-of-stock' : ''}`}>
                      <Link to={`/products/${p.id}`} className="product-image-container">
                        <img
                          src={imgUrl}
                          alt={p.title}
                          className="product-card-img"
                          loading="lazy"
                          onError={(e) => handleProductImageError(e, p.id)}
                        />
                        {p.stock <= 5 && p.stock > 0 && (
                          <span className="stock-alert-badge low">Only {p.stock} left</span>
                        )}
                        {p.stock === 0 && (
                          <span className="stock-alert-badge out">Out of Stock</span>
                        )}
                      </Link>

                      <div className="product-card-body">
                        <div className="product-card-meta">
                          <span className="product-category-tag">{p.category}</span>
                          <span className="product-sku">{p.sku}</span>
                        </div>
                        <Link to={`/products/${p.id}`} className="product-title-link">
                          <h3 className="product-title">{p.title}</h3>
                        </Link>
                        {p.title_ta && <p className="product-tamil-title">{p.title_ta}</p>}

                        <div className="product-pricing">
                          <span className="product-price">
                            ₹{Number(p.price_inr).toLocaleString('en-IN')}
                          </span>
                          <span className={`product-stock-status ${p.stock > 0 ? 'in' : 'out'}`}>
                            {p.stock > 0 ? 'In stock' : 'Out of stock'}
                          </span>
                        </div>

                        <div className="product-card-actions">
                          <button
                            type="button"
                            className="btn-add-cart"
                            onClick={() => void addItem(p.id, 1)}
                            disabled={p.stock <= 0}
                          >
                            <BagIcon size={14} />
                            <span>{p.stock > 0 ? 'Add to Cart' : 'Sold Out'}</span>
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

              {/* Pagination controls */}
              {totalPages > 1 && (
                <div className="pagination-bar">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => updateParam('page', (page - 1).toString())}
                    className="pagination-btn"
                  >
                    &larr; Previous
                  </button>
                  <span className="pagination-info">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => updateParam('page', (page + 1).toString())}
                    className="pagination-btn"
                  >
                    Next &rarr;
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
};
