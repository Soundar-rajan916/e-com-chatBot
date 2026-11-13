import React, { useEffect, useState } from 'react';
import { getDemoCustomers } from '../api/client';
import { DemoCustomer } from '../api/types';
import { ChatInput } from '../components/ChatInput';
import { CustomerPicker } from '../components/CustomerPicker';
import { ErrorNotice } from '../components/ErrorNotice';
import { MessageList } from '../components/MessageList';
import { useChat } from '../hooks/useChat';

export const ChatPage: React.FC = () => {
  const [customers, setCustomers] = useState<DemoCustomer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<DemoCustomer | null>(null);
  const [loadingCustomers, setLoadingCustomers] = useState<boolean>(true);
  const [customerError, setCustomerError] = useState<string | null>(null);

  const {
    messages,
    isPending,
    error: chatError,
    sendMessage,
    retryLastMessage,
  } = useChat(selectedCustomer);

  useEffect(() => {
    async function loadCustomers() {
      try {
        setLoadingCustomers(true);
        const data = await getDemoCustomers();
        setCustomers(data);
        if (data.length > 0) {
          setSelectedCustomer(data[0]);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed loading demo customers.';
        setCustomerError(msg);
      } finally {
        setLoadingCustomers(false);
      }
    }
    loadCustomers();
  }, []);

  return (
    <div className="chat-container">
      <div className="chat-card">
        <CustomerPicker
          customers={customers}
          selectedCustomer={selectedCustomer}
          onSelectCustomer={setSelectedCustomer}
          isLoading={loadingCustomers}
        />

        {customerError && (
          <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', color: '#991b1b', fontSize: '0.875rem' }}>
            {customerError}
          </div>
        )}

        <MessageList messages={messages} isPending={isPending} onActionClick={sendMessage} />

        {chatError && (
          <div style={{ padding: '0 1.25rem' }}>
            <ErrorNotice message={chatError} onRetry={retryLastMessage} />
          </div>
        )}

        <ChatInput onSend={(text) => sendMessage(text)} disabled={isPending || !selectedCustomer} />
      </div>
    </div>
  );
};
