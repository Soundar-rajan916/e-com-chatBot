/// <reference types="vite/client" />

interface SupportWidgetApi {
  init: (config?: any) => void;
  open: () => void;
  close: () => void;
  toggle: () => void;
  isOpen: () => boolean;
  setContext: (context: any) => void;
  setLocale: (locale: 'en' | 'ta') => void;
  identify: (customer: { id: string; name?: string; email?: string }) => void;
  destroy: () => void;
}

interface Window {
  SupportWidget?: SupportWidgetApi;
}
