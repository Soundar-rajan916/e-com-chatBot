import { useCallback } from 'react';

export interface WidgetContext {
  type: 'none' | 'product' | 'order';
  id?: string;
  title?: string;
  price_inr?: string | number;
  order_number?: string;
  status?: string;
  total_amount_inr?: string | number;
}

export function useSupportWidget() {
  const openWidget = useCallback(() => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.open();
    }
  }, []);

  const closeWidget = useCallback(() => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.close();
    }
  }, []);

  const toggleWidget = useCallback(() => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.toggle();
    }
  }, []);

  const setWidgetContext = useCallback((context: WidgetContext) => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.setContext(context);
    }
  }, []);

  const askAboutProduct = useCallback((product: { id: string; title: string; price_inr: string | number }) => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.setContext({
        type: 'product',
        id: product.id,
        title: product.title,
        price_inr: product.price_inr,
      });
      window.SupportWidget.open();
    }
  }, []);

  const askAboutOrder = useCallback((order: { order_number: string; status: string; total_amount_inr: string | number }) => {
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.setContext({
        type: 'order',
        order_number: order.order_number,
        status: order.status,
        total_amount_inr: order.total_amount_inr,
      });
      window.SupportWidget.open();
    }
  }, []);

  return {
    openWidget,
    closeWidget,
    toggleWidget,
    setWidgetContext,
    askAboutProduct,
    askAboutOrder,
  };
}
