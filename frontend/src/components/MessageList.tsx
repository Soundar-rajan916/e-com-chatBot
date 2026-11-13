import React, { useEffect, useRef } from 'react';
import { ChatMessageItem } from '../api/types';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  messages: ChatMessageItem[];
  isPending: boolean;
  onActionClick?: (action: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, isPending, onActionClick }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  return (
    <div className="message-list" ref={scrollRef} aria-live="polite" aria-label="Conversation Messages">
      {messages.length === 0 ? (
        <div style={{ margin: 'auto', textAlign: 'center', color: '#94a3b8', fontSize: '0.9rem' }}>
          Start a conversation in English, தமிழ், or Tanglish.
        </div>
      ) : (
        messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onActionClick={onActionClick} />
        ))
      )}

      {isPending && (
        <div className="typing-indicator" aria-label="Assistant is typing">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      )}
    </div>
  );
};
