"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams } from "next/navigation";
import { apiClient, API_BASE_URL } from "@/lib/api";
import { InvoiceDetailResponse } from "@/types/api";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";

export default function InvoiceDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [invoice, setInvoice] = useState<InvoiceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollingError, setPollingError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState<Record<string, string | number | null>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchFullInvoice = useCallback(async () => {
    try {
      const data = await apiClient.getInvoiceDetail(id);
      setInvoice(data);
      // Initialize form
      setFormData({
        vendor_name: data.vendor_name || "",
        invoice_number: data.invoice_number || "",
        invoice_date: data.invoice_date || "",
        due_date: data.due_date || "",
        // Convert numbers safely, or keep as string/null for forms
        subtotal: data.subtotal !== null ? data.subtotal : "",
        tax: data.tax !== null ? data.tax : "",
        total: data.total !== null ? data.total : "",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to fetch invoice details");
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const loadInitial = async () => {
      setLoading(true);
      setError(null);
      await fetchFullInvoice();
      setLoading(false);
    };
    loadInitial();
  }, [id, fetchFullInvoice]);

  useEffect(() => {
    if (!invoice || !id) return;
    const isActive = invoice.status === 'PENDING' || invoice.status === 'EXTRACTING';
    if (!isActive) return;

    let errorCount = 0;
    const intervalId = setInterval(async () => {
      try {
        const statusRes = await apiClient.getInvoiceStatus(id);
        if (statusRes.status !== invoice.status) {
          if (['PROCESSED', 'NEEDS_REVIEW', 'FAILED'].includes(statusRes.status)) {
            await fetchFullInvoice();
          } else {
            setInvoice(prev => prev ? { ...prev, status: statusRes.status } : null);
          }
        }
        errorCount = 0;
        setPollingError(null);
      } catch (err) {
        console.error("Polling error:", err);
        errorCount++;
        if (errorCount >= 5) {
          clearInterval(intervalId);
          setPollingError("Connection lost or server error. Please refresh the page manually.");
        }
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [id, invoice, fetchFullInvoice]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value === "" ? null : value }));
    setSaveSuccess(false);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError(null);
      
      const updated = await apiClient.updateInvoice(id, formData);
      setInvoice(updated);
      setSaveSuccess(true);
      
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save invoice");
    } finally {
      setIsSaving(false);
    }
  };

  if (loading && !invoice) {
    return (
      <div className="text-center py-12 flex justify-center items-center">
        <Spinner /> <span className="ml-2 text-gray-600">Loading invoice details...</span>
      </div>
    );
  }

  if (error && !invoice) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
        {error}
      </div>
    );
  }

  if (!invoice) return null;

  const isProcessing = invoice.status === 'PENDING' || invoice.status === 'EXTRACTING';

  return (
    <div className="flex flex-col h-[calc(100vh-100px)]">
      {/* Header */}
      <div className="mb-4 flex justify-between items-center shrink-0">
        <div className="flex items-center space-x-4">
          <Link href="/invoices" className="text-blue-600 hover:underline text-sm font-medium">
            &larr; Back
          </Link>
          <h1 className="text-xl font-bold text-gray-900 truncate max-w-sm lg:max-w-xl" title={invoice.file_name}>
            {invoice.file_name}
          </h1>
        </div>
        
        <div className="flex items-center space-x-3">
          {pollingError && (
            <div className="text-sm text-red-600 flex items-center mr-4">
               <span>{pollingError}</span>
               <button onClick={() => fetchFullInvoice()} className="ml-3 underline">Refresh</button>
            </div>
          )}
          {isProcessing && <span className="text-blue-600"><Spinner /></span>}
          <StatusBadge status={invoice.status} />
        </div>
      </div>

      {error && (
         <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 shrink-0">
           {error}
         </div>
      )}

      {/* Main Split Screen */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        
        {/* Left Pane: Document Viewer */}
        <div className="lg:w-1/2 bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex flex-col h-[50vh] lg:h-full shadow-inner">
           <iframe 
             src={`${API_BASE_URL}/invoices/${id}/file`} 
             className="w-full h-full border-0"
             title="Invoice Document Viewer"
           />
        </div>

        {/* Right Pane: Inspector / Form */}
        <div className="lg:w-1/2 bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col h-full overflow-hidden">
          <div className="border-b border-gray-200 px-4 py-3 bg-gray-50 flex justify-between items-center shrink-0">
             <h2 className="text-lg font-medium text-gray-900">Extracted Data</h2>
             {invoice.confidence_score !== null && (
                <span className="text-sm text-gray-600 bg-white px-2 py-1 rounded border border-gray-200 shadow-sm">
                  Confidence: <strong className={invoice.confidence_score > 0.8 ? 'text-green-600' : 'text-yellow-600'}>
                    {(invoice.confidence_score * 100).toFixed(0)}%
                  </strong>
                </span>
             )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 lg:p-6 bg-white">
             {invoice.review_reason && (
               <div className="mb-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded">
                 <h3 className="text-sm font-medium text-yellow-800">Validation Issue</h3>
                 <p className="mt-1 text-sm text-yellow-700">{invoice.review_reason}</p>
               </div>
             )}
             
             {invoice.status === 'FAILED' && invoice.logs && invoice.logs.length > 0 && (
               <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-400 rounded">
                 <h3 className="text-sm font-medium text-red-800">Processing Error</h3>
                 <p className="mt-1 text-sm text-red-700">
                   {invoice.logs.slice().reverse().find(log => log.log_level === 'ERROR')?.message || "An unexpected error occurred."}
                 </p>
               </div>
             )}

             <form id="invoice-form" onSubmit={handleSave} className="space-y-6">
                {/* Header Data */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Invoice Number</label>
                    <input 
                      type="text" name="invoice_number" 
                      value={(formData.invoice_number as string) || ''} onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      disabled={isProcessing}
                      placeholder="—"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Vendor Name</label>
                    <input 
                      type="text" name="vendor_name" 
                      value={(formData.vendor_name as string) || ''} onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      disabled={isProcessing}
                      placeholder="—"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Invoice Date</label>
                    <input 
                      type="date" name="invoice_date" 
                      value={(formData.invoice_date as string) || ''} onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      disabled={isProcessing}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Due Date</label>
                    <input 
                      type="date" name="due_date" 
                      value={(formData.due_date as string) || ''} onChange={handleInputChange}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                      disabled={isProcessing}
                    />
                  </div>
                </div>

                {/* Financials */}
                <h3 className="text-md font-medium text-gray-900 border-b pb-2 pt-4">Financials</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Subtotal</label>
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <input 
                        type="number" step="0.01" name="subtotal" 
                        value={formData.subtotal ?? ''} onChange={handleInputChange}
                        className="block w-full rounded-md border-gray-300 pl-3 pr-12 focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                        disabled={isProcessing}
                        placeholder="—"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Tax</label>
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <input 
                        type="number" step="0.01" name="tax" 
                        value={formData.tax ?? ''} onChange={handleInputChange}
                        className="block w-full rounded-md border-gray-300 pl-3 pr-12 focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                        disabled={isProcessing}
                        placeholder="—"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Total</label>
                    <div className="mt-1 relative rounded-md shadow-sm">
                      <input 
                        type="number" step="0.01" name="total" 
                        value={formData.total ?? ''} onChange={handleInputChange}
                        className="block w-full rounded-md border-gray-300 pl-3 pr-12 focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border font-bold"
                        disabled={isProcessing}
                        placeholder="—"
                      />
                    </div>
                  </div>
                </div>

                {/* Line Items - Read Only Display */}
                <h3 className="text-md font-medium text-gray-900 border-b pb-2 pt-4">Line Items</h3>
                <div className="bg-white rounded-md border border-gray-200 overflow-x-auto shadow-sm">
                   <table className="min-w-full divide-y divide-gray-200 text-sm">
                     <thead className="bg-gray-50">
                       <tr>
                         <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                         <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                         <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                         <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                       </tr>
                     </thead>
                     <tbody className="divide-y divide-gray-200">
                        {invoice.line_items.length === 0 ? (
                          <tr>
                            <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                              {isProcessing ? "Extracting line items..." : "No line items found."}
                            </td>
                          </tr>
                        ) : (
                          invoice.line_items.map(item => (
                            <tr key={item.id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-gray-900">{item.description}</td>
                              <td className="px-4 py-3 text-gray-500 text-right">{item.quantity ?? '—'}</td>
                              <td className="px-4 py-3 text-gray-500 text-right">{item.unit_price ?? '—'}</td>
                              <td className="px-4 py-3 font-medium text-gray-900 text-right">{item.amount}</td>
                            </tr>
                          ))
                        )}
                     </tbody>
                   </table>
                </div>

                {/* Processing Logs */}
                {invoice.logs && invoice.logs.length > 0 && (
                   <div className="mt-8 pt-6 border-t border-gray-200">
                     <h3 className="text-sm font-medium text-gray-700 mb-3">Processing Logs</h3>
                     <div className="bg-gray-900 rounded-md p-4 max-h-48 overflow-y-auto text-xs font-mono space-y-2 shadow-inner">
                        {invoice.logs.map(log => (
                          <div key={log.id} className={`${log.log_level === 'ERROR' ? 'text-red-400' : 'text-green-400'}`}>
                            <span className="text-gray-500">[{new Date(log.created_at).toLocaleTimeString()}]</span> 
                            <span className="text-blue-300 ml-2">[{log.stage}]</span> 
                            <span className="ml-2 text-gray-300">{log.message}</span>
                          </div>
                        ))}
                     </div>
                   </div>
                )}
             </form>
          </div>

          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 shrink-0 flex justify-end items-center space-x-4">
             {saveSuccess && <span className="text-sm text-green-600 font-medium">Synced successfully</span>}
             <button
               type="submit"
               form="invoice-form"
               disabled={isProcessing || isSaving}
               className="inline-flex justify-center py-2 px-6 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
             >
               {isSaving ? "Syncing..." : "Approve & Sync"}
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}
