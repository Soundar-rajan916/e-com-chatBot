import React, { createContext, useContext, useEffect, useState } from 'react';
import { addToCart, clearCart, getCart, removeCartItem, updateCartItem } from '../api/client';
import { CartDetail } from '../api/types';

interface CartContextType {
  cart: CartDetail | null;
  isLoading: boolean;
  itemCount: number;
  addItem: (productId: string, quantity?: number) => Promise<void>;
  updateQuantity: (productId: string, quantity: number) => Promise<void>;
  removeItem: (productId: string) => Promise<void>;
  emptyCart: () => Promise<void>;
  refreshCart: () => Promise<void>;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cart, setCart] = useState<CartDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshCart = async () => {
    try {
      const c = await getCart();
      setCart(c);
    } catch {
      setCart(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshCart();
  }, []);

  const addItem = async (productId: string, quantity = 1) => {
    setIsLoading(true);
    try {
      const updated = await addToCart(productId, quantity);
      setCart(updated);
    } finally {
      setIsLoading(false);
    }
  };

  const updateQuantity = async (productId: string, quantity: number) => {
    setIsLoading(true);
    try {
      const updated = await updateCartItem(productId, quantity);
      setCart(updated);
    } finally {
      setIsLoading(false);
    }
  };

  const removeItem = async (productId: string) => {
    setIsLoading(true);
    try {
      const updated = await removeCartItem(productId);
      setCart(updated);
    } finally {
      setIsLoading(false);
    }
  };

  const emptyCart = async () => {
    setIsLoading(true);
    try {
      const updated = await clearCart();
      setCart(updated);
    } finally {
      setIsLoading(false);
    }
  };

  const itemCount = cart?.total_items || 0;

  return (
    <CartContext.Provider
      value={{
        cart,
        isLoading,
        itemCount,
        addItem,
        updateQuantity,
        removeItem,
        emptyCart,
        refreshCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = (): CartContextType => {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return ctx;
};
