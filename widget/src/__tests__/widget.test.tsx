import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { act } from '@testing-library/react';
import { SupportWidget } from '../index';

describe('SupportWidget Shadow DOM Integration', () => {
  beforeEach(async () => {
    await act(async () => {
      SupportWidget.destroy();
    });
  });

  afterEach(async () => {
    await act(async () => {
      SupportWidget.destroy();
    });
  });

  it('initializes host element and mounts inside Shadow DOM', async () => {
    await act(async () => {
      SupportWidget.init({ storeName: 'Test Store' });
    });

    const host = document.getElementById('support-widget-host');
    expect(host).not.toBeNull();
    expect(host?.shadowRoot).not.toBeNull();

    // Verify style tag and mount node inside shadow root
    const styleTag = host?.shadowRoot?.querySelector('style');
    expect(styleTag).not.toBeNull();

    const mount = host?.shadowRoot?.getElementById('support-widget-mount');
    expect(mount).not.toBeNull();
  });

  it('controls open and close state via public API', async () => {
    await act(async () => {
      SupportWidget.init();
    });
    expect(SupportWidget.isOpen()).toBe(false);

    await act(async () => {
      SupportWidget.open();
    });
    expect(SupportWidget.isOpen()).toBe(true);

    const host = document.getElementById('support-widget-host');
    const windowEl = host?.shadowRoot?.querySelector('.support-widget-window');
    expect(windowEl).not.toBeNull();

    await act(async () => {
      SupportWidget.close();
    });
    expect(SupportWidget.isOpen()).toBe(false);
  });

  it('updates context banner and renders properly', async () => {
    await act(async () => {
      SupportWidget.init({ defaultOpen: true });
    });
    await act(async () => {
      SupportWidget.setContext({
        type: 'product',
        id: 'SKU-99',
        title: 'Silk Saree Blue',
      });
    });

    const host = document.getElementById('support-widget-host');
    const contextPill = host?.shadowRoot?.querySelector('.widget-context-pill');
    expect(contextPill).not.toBeNull();
    expect(contextPill?.textContent).toContain('Silk Saree Blue');
  });

  it('destroys completely leaving no artifacts in DOM', async () => {
    await act(async () => {
      SupportWidget.init();
    });
    expect(document.getElementById('support-widget-host')).not.toBeNull();

    await act(async () => {
      SupportWidget.destroy();
    });
    expect(document.getElementById('support-widget-host')).toBeNull();
  });
});
