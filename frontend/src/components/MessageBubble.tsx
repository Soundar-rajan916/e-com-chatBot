import React from 'react';
import { ChatMessageItem } from '../api/types';
import { FormattedMessage } from './FormattedMessage';
import { HandoffBadge } from './HandoffBadge';

interface MessageBubbleProps {
  message: ChatMessageItem;
  onActionClick?: (action: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onActionClick }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-bubble">
        {isUser ? message.content : <FormattedMessage content={message.content} />}
      </div>

      <div className="message-time">{message.timestamp}</div>

      {!isUser && message.requires_human && <HandoffBadge />}

      {!isUser && message.suggested_actions && message.suggested_actions.length > 0 && (
        <div className="suggested-actions" data-testid="suggested-actions">
          {message.suggested_actions.map((action, idx) => (
            <button
              key={idx}
              type="button"
              className="action-chip"
              onClick={() => onActionClick?.(action)}
            >
              {action}
            </button>
          ))}
        </div>
      )}

      {!isUser && (message.intent || message.trace_id) && (
        <details className="assistant-details">
          <summary>Details</summary>
          <dl className="assistant-details-body">
            {message.intent && (
              <>
                <dt>Intent:</dt>
                <dd>{message.intent}</dd>
              </>
            )}
            {message.language && (
              <>
                <dt>Language:</dt>
                <dd>{message.language}</dd>
              </>
            )}
            {message.trace_id && (
              <>
                <dt>Trace ID:</dt>
                <dd>{message.trace_id}</dd>
              </>
            )}
            {message.sources && message.sources.length > 0 && (
              <>
                <dt>Sources:</dt>
                <dd>
                  <ul className="sources-list" data-testid="sources-list">
                    {message.sources.map((s) => (
                      <li key={`${s.type}-${s.id}`} className={`source-item source-${s.type}`}>
                        <span className="source-type-tag">[{s.type}]</span> {s.title}
                      </li>
                    ))}
                  </ul>
                </dd>
              </>
            )}
          </dl>
        </details>
      )}
    </div>
  );
};
