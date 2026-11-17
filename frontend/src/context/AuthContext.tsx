import React, { createContext, useContext, useEffect, useState } from 'react';
import { customerLogin, customerLogout, customerRegister, getCustomerMe } from '../api/client';
import { CustomerAccount } from '../api/types';

interface AuthContextType {
  customer: CustomerAccount | null;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<CustomerAccount>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    phone: string;
    preferred_language?: string;
  }) => Promise<CustomerAccount>;
  logout: () => Promise<void>;
  refreshCustomer: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [customer, setCustomer] = useState<CustomerAccount | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshCustomer = async () => {
    try {
      const me = await getCustomerMe();
      setCustomer(me);
      if (typeof window !== 'undefined' && window.SupportWidget) {
        window.SupportWidget.identify({ id: me.id, name: me.name, email: me.email });
      }
    } catch {
      setCustomer(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshCustomer();
  }, []);

  const login = async (email: string, pass: string) => {
    const acc = await customerLogin({ email, password: pass });
    setCustomer(acc);
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.identify({ id: acc.id, name: acc.name, email: acc.email });
    }
    return acc;
  };

  const register = async (payload: {
    email: string;
    password: string;
    name: string;
    phone: string;
    preferred_language?: string;
  }) => {
    const acc = await customerRegister(payload);
    setCustomer(acc);
    if (typeof window !== 'undefined' && window.SupportWidget) {
      window.SupportWidget.identify({ id: acc.id, name: acc.name, email: acc.email });
    }
    return acc;
  };

  const logout = async () => {
    try {
      await customerLogout();
    } finally {
      setCustomer(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        customer,
        isLoading,
        login,
        register,
        logout,
        refreshCustomer,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
