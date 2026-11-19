import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChatMessageItem, Locale, WidgetConfig, WidgetContext } from './types';
import {
  ChatIcon,
  CloseIcon,
  BagIcon,
  TagIcon,
  PackageIcon,
  HeadphonesIcon,
  UsersIcon,
  ArrowRightIcon,
} from './WidgetIcons';

interface WidgetAppProps {
  config: WidgetConfig;
  context: WidgetContext;
  isOpen: boolean;
  locale: Locale;
  onClose: () => void;
  onToggle: () => void;
  onClearContext: () => void;
  onLocaleChange: (loc: Locale) => void;
}

function renderInline(text: string): React.ReactNode[] {
  const tokenRegex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const parts = text.split(tokenRegex);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

function parseTable(tableLines: string[], key: string): React.ReactNode {
  if (tableLines.length === 0) return null;

  const rows = tableLines.map((line) => {
    const rawCells = line.split('|');
    const startIdx = rawCells[0].trim() === '' ? 1 : 0;
    const endIdx =
      rawCells[rawCells.length - 1].trim() === '' ? rawCells.length - 1 : rawCells.length;
    return rawCells.slice(startIdx, endIdx).map((c) => c.trim());
  });

  if (rows.length === 0) return null;

  const isDelimiter = (row: string[]) =>
    row.length > 0 && row.every((cell) => /^:?-{2,}:?$/.test(cell.trim()));

  let headerRow: string[] | null = null;
  let bodyRows: string[][] = [];

  if (rows.length >= 2 && isDelimiter(rows[1])) {
    headerRow = rows[0];
    bodyRows = rows.slice(2);
  } else {
    bodyRows = rows;
  }

  return (
    <div key={key} className="message-table-wrapper">
      <table className="message-table">
        {headerRow && (
          <thead>
            <tr>
              {headerRow.map((cell, cIdx) => (
                <th key={cIdx}>{renderInline(cell)}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {bodyRows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx}>{renderInline(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderFormattedMessage(content: string): React.ReactNode {
  if (!content) return null;

  const lines = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const elements: React.ReactNode[] = [];
  let currentListItems: React.ReactNode[] = [];
  let isNumberedList = false;
  let currentTableLines: string[] = [];

  const flushTable = () => {
    if (currentTableLines.length > 0) {
      const tableNode = parseTable(currentTableLines, `tbl_${elements.length}`);
      if (tableNode) {
        elements.push(tableNode);
      }
      currentTableLines = [];
    }
  };

  const flushList = () => {
    if (currentListItems.length > 0) {
      const key = `list_${elements.length}`;
      if (isNumberedList) {
        elements.push(
          <ol key={key} className="message-list ordered">
            {currentListItems}
          </ol>
        );
      } else {
        elements.push(
          <ul key={key} className="message-list bullet">
            {currentListItems}
          </ul>
        );
      }
      currentListItems = [];
      isNumberedList = false;
    }
  };

  lines.forEach((rawLine, lineIdx) => {
    const line = rawLine.trim();

    // Markdown table row: "| col1 | col2 |"
    const isTableLine = line.startsWith('|') && (line.endsWith('|') || (line.match(/\|/g) || []).length >= 2);
    if (isTableLine) {
      flushList();
      currentTableLines.push(line);
      return;
    }

    // Flush any ongoing table
    flushTable();

    // Horizontal divider
    if (line === '---' || line === '***') {
      flushList();
      elements.push(<hr key={`hr_${lineIdx}`} className="message-divider" />);
      return;
    }

    // Unordered bullet item: "- item" or "* item" or "• item"
    const bulletMatch = rawLine.match(/^(\s*)[-*•]\s+(.+)$/);
    if (bulletMatch) {
      if (isNumberedList) {
        flushList();
      }
      const itemContent = bulletMatch[2];
      currentListItems.push(
        <li key={`li_${lineIdx}`}>{renderInline(itemContent)}</li>
      );
      return;
    }

    // Numbered item: "1. item"
    const numberedMatch = rawLine.match(/^(\s*)\d+\.\s+(.+)$/);
    if (numberedMatch) {
      if (!isNumberedList && currentListItems.length > 0) {
        flushList();
      }
      isNumberedList = true;
      const itemContent = numberedMatch[2];
      currentListItems.push(
        <li key={`li_${lineIdx}`}>{renderInline(itemContent)}</li>
      );
      return;
    }

    // Non-list line: flush any ongoing list
    flushList();

    if (!line) {
      return;
    }

    // Heading: "### Heading"
    const headingMatch = line.match(/^#{1,4}\s+(.+)$/);
    if (headingMatch) {
      elements.push(
        <div key={`h_${lineIdx}`} className="message-heading">
          {renderInline(headingMatch[1])}
        </div>
      );
      return;
    }

    // Standard paragraph line
    elements.push(
      <p key={`p_${lineIdx}`} className="message-paragraph">
        {renderInline(rawLine)}
      </p>
    );
  });

  flushList();
  flushTable();

  return <div className="widget-formatted-content">{elements}</div>;
}

export const WidgetApp: React.FC<WidgetAppProps> = ({
  config,
  context,
  isOpen,
  locale,
  onClose,
  onToggle,
  onClearContext,
  onLocaleChange,
}) => {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const apiUrl = config.apiUrl || '';

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Restore current chat on mount
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const res = await fetch(`${apiUrl}/chat/current`, {
          credentials: 'include',
        });
        if (res.ok) {
          const data = await res.json();
          if (data.session_id) {
            setSessionId(data.session_id);
            if (Array.isArray(data.messages) && data.messages.length > 0) {
              setMessages(
                data.messages.map((m: any) => ({
                  id: m.id,
                  role: m.role,
                  content: m.content,
                  input_mode: m.input_mode || 'text',
                  timestamp: new Date(m.created_at || Date.now()).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  }),
                }))
              );
            }
          }
        }
      } catch {
        // Ignore session restore error
      }
    };
    void restoreSession();
  }, [apiUrl]);

  // Poll for agent messages when escalated
  useEffect(() => {
    if (!sessionId) return;
    const hasAgentOrHuman = messages.some((m) => m.role === 'agent' || m.requires_human);
    if (!hasAgentOrHuman) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiUrl}/chat/sessions/${sessionId}/messages`, {
          credentials: 'include',
        });
        if (res.ok) {
          const remoteMsgs = await res.json();
          if (Array.isArray(remoteMsgs) && remoteMsgs.length > 0) {
            setMessages((prev) => {
              const existingIds = new Set(prev.map((p) => p.id));
              const newAgentMsgs = remoteMsgs
                .filter((rm: any) => rm.role === 'agent' && !existingIds.has(rm.id))
                .map((rm: any) => ({
                  id: rm.id,
                  role: 'agent' as const,
                  content: rm.content,
                  agent_name: rm.agent_name || 'Support Executive',
                  timestamp: new Date(rm.created_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  }),
                }));
              return newAgentMsgs.length > 0 ? [...prev, ...newAgentMsgs] : prev;
            });
          }
        }
      } catch {
        // Polling failure silent
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [sessionId, messages, apiUrl]);

  const handleSendMessage = useCallback(
    async (textToSend: string) => {
      const trimmed = textToSend.trim();
      if (!trimmed || isLoading) return;

      const userMsgId = `user_${Date.now()}`;
      const userMsg: ChatMessageItem = {
        id: userMsgId,
        role: 'user',
        content: trimmed,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInputVal('');
      setIsLoading(true);

      try {
        const payload: Record<string, unknown> = {
          message: trimmed,
          session_id: sessionId || null,
        };

        if (context.type !== 'none' && context.id) {
          payload.context = {
            type: context.type,
            id: context.id,
          };
        }

        const res = await fetch(`${apiUrl}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'support-widget',
          },
          credentials: 'include',
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          throw new Error('Failed to send message');
        }

        const data = await res.json();
        setSessionId(data.session_id);

        const botMsg: ChatMessageItem = {
          id: `bot_${Date.now()}`,
          role: 'assistant',
          content: data.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          requires_human: data.requires_human,
          suggested_actions: data.suggested_actions,
          intent: data.intent,
          language: data.language,
          trace_id: data.trace_id,
          sources: data.sources,
          actions: data.actions,
        };

        setMessages((prev) => [...prev, botMsg]);

        // Process any returned client actions
        if (Array.isArray(data.actions)) {
          data.actions.forEach((act: { type: string; payload: Record<string, unknown> }) => {
            if (config.onAction) {
              config.onAction(act);
            }
          });
        }
      } catch {
        const errorMsg: ChatMessageItem = {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: 'Unable to reach support service. Please try again in a moment.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [apiUrl, config, context, isLoading, sessionId]
  );

  // Quick reply chips
  const getQuickReplies = (): string[] => {
    if (context.type === 'product') {
      return locale === 'ta'
        ? ['இது ஸ்டாக்கில் உள்ளதா?', 'திரும்பப் பெறும் கொள்கை என்ன?', 'விவரங்களைக் காட்டு']
        : ['Is this in stock?', 'Return policy for this item', 'Show details'];
    }
    if (context.type === 'order') {
      return locale === 'ta'
        ? ['என் ஆர்டர் எங்கே உள்ளது?', 'இதை திரும்பப் பெற விரும்புகிறேன்', 'ஆர்டரை ரத்து செய்']
        : ['Where is this order?', 'I want to return this order', 'Cancel this order'];
    }
    return locale === 'ta'
      ? ['என் ஆர்டர் எங்கே?', 'திரும்பப் பெறும் கொள்கை', 'நேரடி ஆதரவு']
      : ['Track my orders', 'Return Policy', 'Speak with Agent'];
  };

  return (
    <div className="support-widget-container">
      {/* Floating launcher */}
      <button
        type="button"
        className="support-widget-launcher"
        onClick={onToggle}
        aria-label="Toggle Regional Support Assistant"
      >
        {isOpen ? <CloseIcon size={20} /> : <ChatIcon size={22} />}
      </button>

      {/* Main chat window */}
      {isOpen && (
        <div className="support-widget-window">
          {/* Header */}
          <div className="widget-header">
            <div className="widget-header-title">
              <span className="widget-avatar"><BagIcon size={18} /></span>
              <div>
                <div className="widget-brand-name">
                  {config.storeName || 'Regional Support'}
                </div>
                <div className="widget-status-badge">
                  <span className="widget-status-dot" />
                  <span>AI Assistant Online</span>
                </div>
              </div>
            </div>
            <div className="widget-header-controls">
              <button
                type="button"
                className="widget-locale-btn"
                onClick={() => onLocaleChange(locale === 'en' ? 'ta' : 'en')}
              >
                {locale === 'en' ? 'தமிழ்' : 'English'}
              </button>
              <button
                type="button"
                className="widget-close-btn"
                onClick={onClose}
                aria-label="Close Support Widget"
              >
                <CloseIcon size={16} />
              </button>
            </div>
          </div>

          {/* Context Banner */}
          {context.type !== 'none' && (
            <div className="widget-context-pill">
              <span className="widget-context-text">
                {context.type === 'product' ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <TagIcon size={12} /> Product:
                  </span>
                ) : (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <PackageIcon size={12} /> Order:
                  </span>
                )}{' '}
                <strong>{context.title || context.id}</strong>
              </span>
              <button
                type="button"
                className="widget-context-clear"
                onClick={onClearContext}
                title="Clear Context"
                aria-label="Clear Context"
              >
                <CloseIcon size={12} />
              </button>
            </div>
          )}

          {/* Messages */}
          <div className="widget-messages">
            {messages.length === 0 && (
              <div style={{ margin: 'auto', textAlign: 'center', color: '#94a3b8' }}>
                <p style={{ margin: '0 0 4px', fontWeight: 600 }}>
                  {locale === 'ta'
                    ? 'வணக்கம்! நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?'
                    : 'Hello! How can I help you today?'}
                </p>
                <p style={{ margin: 0, fontSize: '12px' }}>
                  Ask about products, orders, returns in English or தமிழ்.
                </p>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.id} className={`widget-message-item ${m.role}`}>
                {m.role === 'agent' && (
                  <span className="widget-agent-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <HeadphonesIcon size={12} /> {m.agent_name || 'Support Executive'}
                  </span>
                )}
                <div className="widget-bubble">{renderFormattedMessage(m.content)}</div>
                {m.requires_human && (
                  <div className="widget-handoff-banner" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <UsersIcon size={14} />
                    <span>Handed to a support executive</span>
                  </div>
                )}
                {m.trace_id && (
                  <details className="widget-details">
                    <summary>Why this answer</summary>
                    <div className="widget-details-content">
                      <div>
                        <strong>Intent:</strong> {m.intent || '—'}
                      </div>
                      <div>
                        <strong>Language:</strong> {m.language || '—'}
                      </div>
                      {m.sources && m.sources.length > 0 && (
                        <div>
                          <strong>Sources:</strong> {m.sources.map((s) => s.title).join(', ')}
                        </div>
                      )}
                    </div>
                  </details>
                )}
                <span className="widget-time">{m.timestamp}</span>
              </div>
            ))}

            {isLoading && (
              <div className="widget-typing" aria-label="Assistant is typing">
                <span className="widget-typing-dot" />
                <span className="widget-typing-dot" />
                <span className="widget-typing-dot" />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Replies */}
          <div className="widget-quick-replies">
            {getQuickReplies().map((chip, idx) => (
              <button
                key={idx}
                type="button"
                className="widget-chip"
                onClick={() => void handleSendMessage(chip)}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form
            className="widget-input-bar"
            onSubmit={(e) => {
              e.preventDefault();
              void handleSendMessage(inputVal);
            }}
          >
            <input
              type="text"
              className="widget-text-input"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder={
                locale === 'ta'
                  ? 'கேள்வி அல்லது செய்தியைத் தட்டச்சு செய்க...'
                  : 'Type your question or message...'
              }
              disabled={isLoading}
            />
            {/* Send Button */}
            <button
              type="submit"
              className="widget-send-btn"
              disabled={isLoading || !inputVal.trim()}
              aria-label="Send message"
            >
              <ArrowRightIcon size={15} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
