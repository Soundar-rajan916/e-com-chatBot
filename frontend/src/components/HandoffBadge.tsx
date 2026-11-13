import React from 'react';

export const HandoffBadge: React.FC = () => {
  return (
    <div className="handoff-badge" role="status" aria-label="Support Executive Handoff">
      <span>🤝</span>
      <span>Handed to a support executive</span>
    </div>
  );
};
