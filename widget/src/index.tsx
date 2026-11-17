import React from 'react';
import ReactDOM from 'react-dom/client';
import { Locale, SupportWidgetApi, WidgetConfig, WidgetContext } from './types';
import { WidgetApp } from './WidgetApp';
// Import css inline as a raw string so it can be injected directly into the Shadow DOM
import widgetStyles from './widget.css?inline';

class SupportWidgetManager {
  private hostEl: HTMLElement | null = null;
  private shadowRoot: ShadowRoot | null = null;
  private reactRoot: ReactDOM.Root | null = null;
  private config: WidgetConfig = {};
  private context: WidgetContext = { type: 'none' };
  private locale: Locale = 'en';
  private isOpenState = false;

  public init(config: WidgetConfig = {}): void {
    this.config = { ...this.config, ...config };
    if (config.initialLocale) {
      this.locale = config.initialLocale;
    }
    if (config.defaultOpen !== undefined) {
      this.isOpenState = config.defaultOpen;
    }

    if (this.hostEl) {
      this.render();
      return;
    }

    // Create host element
    this.hostEl = document.createElement('div');
    this.hostEl.id = 'support-widget-host';
    document.body.appendChild(this.hostEl);

    // Attach Shadow DOM for 100% style isolation
    this.shadowRoot = this.hostEl.attachShadow({ mode: 'open' });

    // Inject styles
    const styleEl = document.createElement('style');
    styleEl.textContent = widgetStyles;
    this.shadowRoot.appendChild(styleEl);

    // Create react mount node
    const mountNode = document.createElement('div');
    mountNode.id = 'support-widget-mount';
    this.shadowRoot.appendChild(mountNode);

    this.reactRoot = ReactDOM.createRoot(mountNode);
    this.render();
  }

  public open(): void {
    this.isOpenState = true;
    this.render();
  }

  public close(): void {
    this.isOpenState = false;
    this.render();
  }

  public toggle(): void {
    this.isOpenState = !this.isOpenState;
    this.render();
  }

  public isOpen(): boolean {
    return this.isOpenState;
  }

  public setContext(context: WidgetContext): void {
    this.context = { ...context };
    this.render();
  }

  public setLocale(locale: Locale): void {
    this.locale = locale;
    this.render();
  }

  public identify(_customer: { id: string; name?: string; email?: string }): void {
    // If the widget is open and customer identified, re-render
    this.render();
  }

  public destroy(): void {
    if (this.reactRoot) {
      this.reactRoot.unmount();
      this.reactRoot = null;
    }
    if (this.hostEl && this.hostEl.parentNode) {
      this.hostEl.parentNode.removeChild(this.hostEl);
      this.hostEl = null;
      this.shadowRoot = null;
    }
    this.isOpenState = false;
  }

  private render(): void {
    if (!this.reactRoot) return;

    this.reactRoot.render(
      <React.StrictMode>
        <WidgetApp
          config={this.config}
          context={this.context}
          isOpen={this.isOpenState}
          locale={this.locale}
          onClose={() => this.close()}
          onToggle={() => this.toggle()}
          onClearContext={() => this.setContext({ type: 'none' })}
          onLocaleChange={(loc) => this.setLocale(loc)}
        />
      </React.StrictMode>
    );
  }
}

const instance = new SupportWidgetManager();

export const SupportWidget: SupportWidgetApi = {
  init: (cfg) => instance.init(cfg),
  open: () => instance.open(),
  close: () => instance.close(),
  toggle: () => instance.toggle(),
  isOpen: () => instance.isOpen(),
  setContext: (ctx) => instance.setContext(ctx),
  setLocale: (loc) => instance.setLocale(loc),
  identify: (cust) => instance.identify(cust),
  destroy: () => instance.destroy(),
};

// Expose globally on window
if (typeof window !== 'undefined') {
  window.SupportWidget = SupportWidget;
}

export default SupportWidget;
