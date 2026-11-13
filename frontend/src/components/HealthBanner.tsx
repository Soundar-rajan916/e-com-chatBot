import React from 'react';

interface HealthBannerProps {
  isHealthy: boolean;
  message: string | null;
}

export const HealthBanner: React.FC<HealthBannerProps> = ({ isHealthy, message }) => {
  if (isHealthy) return null;

  return (
    <div className="health-banner error" role="alert">
      <span>⚠️</span>
      <span>
        Service unavailable, retrying... {message ? `(${message})` : ''}
      </span>
    </div>
  );
};
