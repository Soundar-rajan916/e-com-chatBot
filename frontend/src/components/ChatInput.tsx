import React, { useState } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

const MAX_CHARS = 1000;

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [text, setText] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (trimmed && !disabled && trimmed.length <= MAX_CHARS) {
      onSend(trimmed);
      setText('');
    }
  };

  const charCount = text.length;
  const isNearLimit = charCount >= 900;
  const isAtLimit = charCount >= MAX_CHARS;

  return (
    <div className="chat-input-bar">
      <div className="chat-input-container">
        <textarea
          className="chat-textarea"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKeyDown}
          placeholder="Type your message in English, தமிழ், or Tanglish..."
          disabled={disabled}
          maxLength={MAX_CHARS}
          rows={1}
          aria-label="Chat Message Input"
        />
        <button
          type="button"
          className="send-button"
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          aria-label="Send Message"
        >
          Send
        </button>
      </div>

      <div className="input-footer">
        <span>Enter to send, Shift+Enter for new line</span>
        <span
          className={`char-counter ${isAtLimit ? 'danger' : isNearLimit ? 'warning' : ''}`}
          aria-label={`${charCount} of ${MAX_CHARS} characters used`}
        >
          {charCount}/{MAX_CHARS}
        </span>
      </div>
    </div>
  );
};
