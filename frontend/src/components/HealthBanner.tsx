import React from 'react';
import { AlertCircleIcon } from './icons';

interface HealthBannerProps {
  isHealthy: boolean;
  message: string | null;
}

export const HealthBanner: React.FC<HealthBannerProps> = ({ isHealthy, message }) => {
  if (isHealthy) return null;

  return (
    <div className="health-banner error" role="alert">
      <AlertCircleIcon size={16} />
      <span>
        Service unavailable, retrying... {message ? `(${message})` : ''}
      </span>
    </div>
  );
};
