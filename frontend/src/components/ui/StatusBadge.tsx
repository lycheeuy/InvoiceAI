import React from 'react';
import { InvoiceStatus } from '@/types/api';

export const STATUS_MAPPING: Record<InvoiceStatus, { label: string, color: string }> = {
  PENDING: { label: 'Queued', color: 'bg-gray-100 text-gray-800 border-gray-200' },
  EXTRACTING: { label: 'Processing', color: 'bg-blue-100 text-blue-800 border-blue-200' },
  PROCESSED: { label: 'Processed', color: 'bg-green-100 text-green-800 border-green-200' },
  NEEDS_REVIEW: { label: 'Needs Review', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  FAILED: { label: 'Failed', color: 'bg-red-100 text-red-800 border-red-200' },
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  const mapping = STATUS_MAPPING[status] || { label: status, color: 'bg-gray-100 text-gray-800 border-gray-200' };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${mapping.color}`}>
      {status === 'EXTRACTING' && (
        <svg className="animate-spin -ml-1 mr-1.5 h-3 w-3 text-blue-800" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )}
      {mapping.label}
    </span>
  );
}
