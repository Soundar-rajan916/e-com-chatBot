import React from 'react';
import { DemoCustomer } from '../api/types';

interface CustomerPickerProps {
  customers: DemoCustomer[];
  selectedCustomer: DemoCustomer | null;
  onSelectCustomer: (customer: DemoCustomer) => void;
  isLoading: boolean;
}

export const CustomerPicker: React.FC<CustomerPickerProps> = ({
  customers,
  selectedCustomer,
  onSelectCustomer,
  isLoading,
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const found = customers.find((c) => c.id === e.target.value);
    if (found) {
      onSelectCustomer(found);
    }
  };

  return (
    <div className="customer-picker-bar">
      <label htmlFor="customer-select" className="customer-picker-label">
        Active Customer:
      </label>
      <select
        id="customer-select"
        className="customer-select"
        value={selectedCustomer?.id || ''}
        onChange={handleChange}
        disabled={isLoading || customers.length === 0}
        aria-label="Select Demo Customer"
      >
        {customers.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.phone}) - {(c.preferred_language || 'en').toUpperCase()}
          </option>
        ))}
      </select>
      {selectedCustomer && (
        <span className="customer-lang-pill" aria-label={`Preferred language: ${selectedCustomer.preferred_language}`}>
          Lang: {selectedCustomer.preferred_language}
        </span>
      )}
    </div>
  );
};
