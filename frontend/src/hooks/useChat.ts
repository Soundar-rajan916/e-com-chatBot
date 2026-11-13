import { useCallback, useEffect, useState } from 'react';
import { ApiError, pollSessionMessages, sendMessage as sendApiMessage } from '../api/client';
import { ChatMessageItem, DemoCustomer } from '../api/types';

interface StoredSessionState {
  sessionId: string | null;
  messages: ChatMessageItem[];
}

export function useChat(selectedCustomer: DemoCustomer | null) {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isPending, setIsPending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Check if case was escalated / requires human
  const hasHumanEscalation = messages.some((m) => m.requires_human || m.role === 'agent');

  // Load conversation from sessionStorage when customer changes
  useEffect(() => {
    if (!selectedCustomer) {
      setMessages([]);
      setSessionId(null);
      setError(null);
      setLastFailedMessage(null);
      return;
    }

    try {
      const storageKey = `ecom_chat_${selectedCustomer.id}`;
      const saved = sessionStorage.getItem(storageKey);
      if (saved) {
        const parsed: StoredSessionState = JSON.parse(saved);
        setSessionId(parsed.sessionId);
        setMessages(parsed.messages || []);
      } else {
        setSessionId(null);
        setMessages([]);
      }
    } catch {
      setSessionId(null);
      setMessages([]);
    }
    setError(null);
    setLastFailedMessage(null);
  }, [selectedCustomer]);

  // Persist conversation to sessionStorage whenever messages or sessionId change
  useEffect(() => {
    if (!selectedCustomer) return;
    try {
      const storageKey = `ecom_chat_${selectedCustomer.id}`;
      const stateToStore: StoredSessionState = {
        sessionId,
        messages,
      };
      sessionStorage.setItem(storageKey, JSON.stringify(stateToStore));
    } catch {
      // Ignore quota or private browsing errors safely
    }
  }, [selectedCustomer, sessionId, messages]);

  // Background polling for agent replies when human handoff is active
  useEffect(() => {
    if (!selectedCustomer || !sessionId || !hasHumanEscalation) return;

    let isMounted = true;
    const intervalId = setInterval(async () => {
      try {
        const serverMessages = await pollSessionMessages(sessionId, selectedCustomer.id);
        if (!isMounted || !serverMessages || serverMessages.length === 0) return;

        setMessages((prev) => {
          // Check if any agent messages on server are not in client
          const existingContents = new Set(prev.map((m) => `${m.role}_${m.content}`));
          const newAgentMessages = serverMessages
            .filter((sm) => sm.role === 'agent' && !existingContents.has(`${sm.role}_${sm.content}`))
            .map((sm) => ({
              id: sm.id,
              role: 'agent' as const,
              content: sm.content,
              timestamp: new Date(sm.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              }),
              agent_name: sm.agent_name,
              input_mode: sm.input_mode,
            }));

          if (newAgentMessages.length > 0) {
            return [...prev, ...newAgentMessages];
          }
          return prev;
        });
      } catch {
        // Silently ignore background polling errors
      }
    }, 3000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [selectedCustomer, sessionId, hasHumanEscalation]);

  const sendMessage = useCallback(
    async (text: string, isRetry = false) => {
      const trimmed = text.trim();
      if (!trimmed || !selectedCustomer || isPending) return;

      setIsPending(true);
      setError(null);
      setLastFailedMessage(null);

      // Only add to messages list if this is NOT a retry resend
      if (!isRetry) {
        const userMsg: ChatMessageItem = {
          id: `msg_u_${Date.now()}_${Math.random()}`,
          role: 'user',
          content: trimmed,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, userMsg]);
      }

      try {
        const response = await sendApiMessage({
          customer_id: selectedCustomer.id,
          session_id: sessionId,
          message: trimmed,
        });

        setSessionId(response.session_id);

        const assistantMsg: ChatMessageItem = {
          id: `msg_a_${Date.now()}_${Math.random()}`,
          role: 'assistant',
          content: response.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          intent: response.intent,
          language: response.language,
          requires_human: response.requires_human,
          trace_id: response.trace_id,
          sources: response.sources,
          suggested_actions: response.suggested_actions,
          structured_output: response.structured_output,
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        const userFacing = err instanceof ApiError ? err.userMessage : 'An error occurred sending your message.';
        setError(userFacing);
        setLastFailedMessage(trimmed);
      } finally {
        setIsPending(false);
      }
    },
    [selectedCustomer, sessionId, isPending]
  );

  const retryLastMessage = useCallback(() => {
    if (lastFailedMessage) {
      sendMessage(lastFailedMessage, true);
    }
  }, [lastFailedMessage, sendMessage]);

  const clearChat = useCallback(() => {
    if (selectedCustomer) {
      try {
        sessionStorage.removeItem(`ecom_chat_${selectedCustomer.id}`);
      } catch {
        // Safe catch
      }
    }
    setSessionId(null);
    setMessages([]);
    setError(null);
    setLastFailedMessage(null);
  }, [selectedCustomer]);

  return {
    messages,
    sessionId,
    isPending,
    error,
    sendMessage,
    retryLastMessage,
    clearChat,
  };
}
