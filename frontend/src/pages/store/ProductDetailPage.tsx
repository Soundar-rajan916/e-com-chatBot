import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getProduct, getRelatedProducts } from '../../api/client';
import { ProductItem } from '../../api/types';
import { useCart } from '../../context/CartContext';
import { useSupportWidget } from '../../hooks/useSupportWidget';
import { getProductImageUrl, handleProductImageError } from '../../utils/productImages';
import { BagIcon, ShieldCheckIcon, RulerIcon, ChatIcon, CheckIcon } from '../../components/icons';

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<ProductItem | null>(null);
  const [related, setRelated] = useState<ProductItem[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [addedNotice, setAddedNotice] = useState(false);

  const { addItem, cart } = useCart();
  const { askAboutProduct } = useSupportWidget();

  const inCartItem = cart?.items?.find((i) => i.product_id === product?.id);
  const inCartQty = inCartItem?.quantity || 0;
  const productStock = Number(product?.stock ?? 0);
  const remainingStock = Math.max(0, productStock - inCartQty);
  const maxAddable = Math.min(remainingStock, 10);

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    setQuantity(1);
    setAddedNotice(false);

    async function loadProduct() {
      try {
        const p = await getProduct(id!);
        setProduct(p);
        const rel = await getRelatedProducts(id!).catch(() => []);
        setRelated(rel);
      } catch (err) {
        console.error('Failed to load product details', err);
      } finally {
        setIsLoading(false);
      }
    }
    void loadProduct();
  }, [id]);

  const handleAddToCart = async () => {
    if (!product || remainingStock <= 0) return;
    await addItem(product.id, quantity);
    setQuantity(1);
    setAddedNotice(true);
    setTimeout(() => setAddedNotice(false), 3000);
  };

  if (isLoading) {
    return <div className="detail-loading-container">Loading product details...</div>;
  }

  if (!product) {
    return (
      <div className="product-not-found">
        <h2>Product Not Found</h2>
        <p>The requested product does not exist or has been removed.</p>
        <Link to="/products" className="btn-back-catalog">
          &larr; Back to Products
        </Link>
      </div>
    );
  }

  const imgUrl = getProductImageUrl(product);

  return (
    <div className="product-detail-page">
      <div className="breadcrumb-nav">
        <Link to="/">Home</Link> &gt; <Link to="/products">Products</Link> &gt;{' '}
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>
          {product.category}
        </Link>{' '}
        &gt; <span>{product.title}</span>
      </div>

      <div className="product-detail-container">
        {/* Left: Product Image */}
        <div className="detail-image-box">
          <img
            src={imgUrl}
            alt={product.title}
            className="detail-main-img"
            loading="lazy"
            style={{ width: '100%', aspectRatio: '3/4', objectFit: 'cover' }}
            onError={(e) => handleProductImageError(e, product.id)}
          />
          <div className="image-sku-badge">SKU: {product.sku}</div>
          {/* Photographer credit line on Product Detail Page only */}
          {((import.meta.env.VITE_SHOW_IMAGE_CREDITS ?? 'true') !== 'false') && product.image_credit && (
            <div
              className="detail-image-credit"
              style={{
                fontSize: '0.75rem',
                color: '#64748b',
                marginTop: '8px',
                textAlign: 'center',
                lineHeight: 1.4,
              }}
            >
              <span style={{ opacity: 0.8 }}>Photo credit / புகைப்பட உதவி: </span>
              <span style={{ fontWeight: 500 }}>{product.image_credit}</span>
            </div>
          )}
        </div>

        {/* Right: Product Info & Actions */}
        <div className="detail-info-box">
          <span className="detail-category-pill">{product.category}</span>
          <h1 className="detail-title">{product.title}</h1>
          {product.title_ta && <h2 className="detail-tamil-title">{product.title_ta}</h2>}

          <div className="detail-price-row">
            <span className="detail-price">
              ₹{Number(product.price_inr).toLocaleString('en-IN')}
            </span>
            <span className="detail-tax-note">Inclusive of all taxes</span>
          </div>

          <div className="detail-stock-row">
            <span className={`stock-status-pill ${productStock > 0 ? 'instock' : 'outstock'}`}>
              {productStock > 0 ? `In Stock (${productStock} units available)` : 'Out of Stock'}
            </span>
            {inCartQty > 0 && (
              <span className="cart-existing-badge" title="Units already added to your cart" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <BagIcon size={13} /> {inCartQty} in cart
              </span>
            )}
            <span className="return-policy-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheckIcon size={14} /> 7-Day Hassle-Free Returns
            </span>
          </div>

          {/* Description Section */}
          <div className="detail-description-section">
            <h3>Description</h3>
            <p className="detail-description-text">{product.description || 'No description available.'}</p>
            {product.description_ta && (
              <div className="detail-tamil-desc">
                <h4>விளக்கம் (Tamil)</h4>
                <p>{product.description_ta}</p>
              </div>
            )}
          </div>

          {/* Men's Size Selection */}
          <div className="detail-size-selection" style={{ margin: '16px 0' }}>
            <div className="size-label-row" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
              <span className="size-title">Select Size:</span>
              <span className="size-guide-hint" style={{ color: '#0d9488', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <RulerIcon size={14} /> Men's Fit Guide
              </span>
            </div>
            <div className="size-pills-row" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {['formal_shirts', 'casual_shirts', 'tshirts_polos', 'blazers_suits', 'mens_wear'].includes(product.category) ? (
                ['38 (S)', '40 (M)', '42 (L)', '44 (XL)', '46 (XXL)'].map((sz, idx) => (
                  <button
                    key={sz}
                    type="button"
                    className="size-pill-btn"
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      border: idx === 1 ? '2px solid #0f172a' : '1px solid #cbd5e1',
                      background: idx === 1 ? '#0f172a' : '#ffffff',
                      color: idx === 1 ? '#ffffff' : '#1e293b',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {sz}
                  </button>
                ))
              ) : product.category === 'trousers_chinos' ? (
                ['30W', '32W', '34W', '36W', '38W'].map((sz, idx) => (
                  <button
                    key={sz}
                    type="button"
                    className="size-pill-btn"
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      border: idx === 1 ? '2px solid #0f172a' : '1px solid #cbd5e1',
                      background: idx === 1 ? '#0f172a' : '#ffffff',
                      color: idx === 1 ? '#ffffff' : '#1e293b',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {sz}
                  </button>
                ))
              ) : product.category === 'footwear' ? (
                ['UK 7', 'UK 8', 'UK 9', 'UK 10', 'UK 11'].map((sz, idx) => (
                  <button
                    key={sz}
                    type="button"
                    className="size-pill-btn"
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      border: idx === 1 ? '2px solid #0f172a' : '1px solid #cbd5e1',
                      background: idx === 1 ? '#0f172a' : '#ffffff',
                      color: idx === 1 ? '#ffffff' : '#1e293b',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {sz}
                  </button>
                ))
              ) : product.category === 'dhotis_ethnic' ? (
                ['4 Mulam (Single)', '8 Mulam (Double / Wedding)', '9x5 Panchakacham'].map((sz, idx) => (
                  <button
                    key={sz}
                    type="button"
                    className="size-pill-btn"
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      border: idx === 1 ? '2px solid #0f172a' : '1px solid #cbd5e1',
                      background: idx === 1 ? '#0f172a' : '#ffffff',
                      color: idx === 1 ? '#ffffff' : '#1e293b',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {sz}
                  </button>
                ))
              ) : (
                ['One Size / Regular'].map((sz) => (
                  <button
                    key={sz}
                    type="button"
                    className="size-pill-btn"
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      border: '2px solid #0f172a',
                      background: '#0f172a',
                      color: '#ffffff',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {sz}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Purchasing actions */}
          <div className="detail-purchase-controls">
            {productStock > 0 && remainingStock > 0 && (
              <div className="quantity-picker">
                <label htmlFor="qty-select">Quantity:</label>
                <div className="quantity-buttons">
                  <button
                    type="button"
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    disabled={quantity <= 1}
                  >
                    -
                  </button>
                  <span className="quantity-value">{quantity}</span>
                  <button
                    type="button"
                    onClick={() => setQuantity((q) => Math.min(maxAddable, q + 1))}
                    disabled={quantity >= maxAddable}
                  >
                    +
                  </button>
                </div>
              </div>
            )}

            <div className="detail-action-buttons">
              <button
                type="button"
                className="btn-detail-add-cart"
                onClick={() => void handleAddToCart()}
                disabled={productStock <= 0 || remainingStock <= 0}
              >
                {productStock <= 0
                  ? 'Currently Unavailable'
                  : remainingStock <= 0
                  ? 'All Available Stock in Cart'
                  : 'Add to Shopping Cart'}
              </button>

              <button
                type="button"
                className="btn-detail-ask-ai"
                onClick={() =>
                  askAboutProduct({
                    id: product.id,
                    title: product.title,
                    price_inr: product.price_inr,
                  })
                }
                style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <ChatIcon size={16} /> Ask AI about this product (தமிழ் / English)
              </button>
            </div>

            {addedNotice && (
              <div className="added-to-cart-toast" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                <CheckIcon size={16} /> Added {quantity} item(s) to cart! <Link to="/cart">View Cart &rarr;</Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Related Products Section */}
      {related.length > 0 && (
        <section className="related-products-section">
          <h2>Similar &amp; Complementary Products</h2>
          <div className="products-grid">
            {related.map((rp) => {
              const rImgUrl = getProductImageUrl(rp);
              return (
                <div key={rp.id} className="product-card">
                  <Link to={`/products/${rp.id}`} className="product-image-container">
                    <img
                      src={rImgUrl}
                      alt={rp.title}
                      className="product-card-img"
                      onError={(e) => handleProductImageError(e, rp.id)}
                    />
                  </Link>
                  <div className="product-card-body">
                    <span className="product-category-tag">{rp.category}</span>
                    <Link to={`/products/${rp.id}`} className="product-title-link">
                      <h3 className="product-title">{rp.title}</h3>
                    </Link>
                    <div className="product-pricing">
                      <span className="product-price">
                        ₹{Number(rp.price_inr).toLocaleString('en-IN')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
};
