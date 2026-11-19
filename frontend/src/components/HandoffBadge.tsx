import React from 'react';
import { UsersIcon } from './icons';

export const HandoffBadge: React.FC = () => {
  return (
    <div className="handoff-badge" role="status" aria-label="Support Executive Handoff">
      <UsersIcon size={14} />
      <span>Handed to a support executive</span>
    </div>
  );
};
