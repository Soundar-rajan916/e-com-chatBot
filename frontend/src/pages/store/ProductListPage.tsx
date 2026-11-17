import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getBaseUrl, getCategories, getProducts } from '../../api/client';
import { CategoryItem, ProductItem } from '../../api/types';
import { useCart } from '../../context/CartContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';

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
      <div className="catalog-header">
        <h1>Product Catalog</h1>
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
                placeholder="Search products, sarees, cookware..."
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
                  {cat.icon ? `${cat.icon} ` : ''}{cat.category.replace(/_/g, ' ')}
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
                  const imgUrl = `${getBaseUrl()}/products/${p.id}/image.svg`;
                  return (
                    <div key={p.id} className="product-card">
                      <Link to={`/products/${p.id}`} className="product-image-container">
                        <img src={imgUrl} alt={p.title} className="product-card-img" />
                        {p.stock <= 5 && p.stock > 0 && (
                          <span className="stock-alert-badge">Only {p.stock} left</span>
                        )}
                        {p.stock === 0 && (
                          <span className="stock-alert-badge out">Out of Stock</span>
                        )}
                      </Link>

                      <div className="product-card-body">
                        <span className="product-category-tag">{p.category}</span>
                        <Link to={`/products/${p.id}`} className="product-title-link">
                          <h3 className="product-title">{p.title}</h3>
                        </Link>
                        {p.title_ta && <p className="product-tamil-title">{p.title_ta}</p>}

                        <div className="product-pricing">
                          <span className="product-price">
                            ₹{Number(p.price_inr).toLocaleString('en-IN')}
                          </span>
                          <span className="product-sku">SKU: {p.sku}</span>
                        </div>

                        <div className="product-card-actions">
                          <button
                            type="button"
                            className="btn-add-cart"
                            onClick={() => void addItem(p.id, 1)}
                            disabled={p.stock <= 0}
                          >
                            {p.stock > 0 ? 'Add to Cart' : 'Sold Out'}
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
                          >
                            Ask AI
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
