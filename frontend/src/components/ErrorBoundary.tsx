import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in UI component tree:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '3rem 1.5rem',
          maxWidth: '600px',
          margin: '4rem auto',
          textAlign: 'center',
          fontFamily: 'Inter, system-ui, sans-serif',
          background: '#ffffff',
          borderRadius: '12px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛍️</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.5rem' }}>
            Oops! Something went wrong
          </h2>
          <p style={{ color: '#64748b', fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '1.5rem' }}>
            We encountered an unexpected interface error. Click below to reload the storefront.
          </p>
          {this.state.error && (
            <pre style={{
              background: '#f8fafc',
              padding: '0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              color: '#dc2626',
              textAlign: 'left',
              overflowX: 'auto',
              marginBottom: '1.5rem'
            }}>
              {this.state.error.message}
            </pre>
          )}
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              background: '#2563eb',
              color: '#ffffff',
              border: 'none',
              padding: '0.65rem 1.5rem',
              borderRadius: '8px',
              fontSize: '0.95rem',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
