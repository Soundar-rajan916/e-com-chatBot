import React from 'react';

interface ErrorNoticeProps {
  message: string;
  onRetry: () => void;
}

export const ErrorNotice: React.FC<ErrorNoticeProps> = ({ message, onRetry }) => {
  return (
    <div className="error-notice" role="alert">
      <div className="error-notice-text">
        <strong>Error: </strong>
        {message}
      </div>
      <button type="button" className="retry-button" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
};
