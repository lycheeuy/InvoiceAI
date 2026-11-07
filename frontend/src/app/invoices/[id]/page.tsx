"use client";

import { useEffect, useState, useCallback, FormEvent } from "react";
import { useParams } from "next/navigation";
import { apiClient, API_BASE_URL } from "@/lib/api";
import { InvoiceDetailResponse, InvoiceLineItemUpdatePayload, InvoiceUpdatePayload } from "@/types/api";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Spinner } from "@/components/ui/Spinner";

interface EditableLineItem {
  localId: string;
  id?: string | null;
  description: string;
  quantity: string | number | null;
  unit_price: string | number | null;
  amount: string | number | null;
}

const mapApiLineItemsToEditable = (
  items: InvoiceDetailResponse["line_items"] | undefined
): EditableLineItem[] => {
  if (!items || !Array.isArray(items)) return [];
  return items.map((item, idx) => ({
    localId: item.id || `item-${idx}-${Date.now()}`,
    id: item.id ?? null,
    description: item.description ?? "",
    quantity: item.quantity !== null && item.quantity !== undefined ? item.quantity : "",
    unit_price: item.unit_price !== null && item.unit_price !== undefined ? item.unit_price : "",
    amount: item.amount !== null && item.amount !== undefined ? item.amount : "",
  }));
};

export default function InvoiceDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [invoice, setInvoice] = useState<InvoiceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollingError, setPollingError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState<Record<string, string | number | null>>({});
  const [lineItems, setLineItems] = useState<EditableLineItem[]>([]);
  const [isLineItemsDirty, setIsLineItemsDirty] = useState(false);
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
      setLineItems(mapApiLineItemsToEditable(data.line_items));
      setIsLineItemsDirty(false);
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

  const normalizeMonetaryInput = (val: string | number | null | undefined): string | number | null => {
    if (val === null || val === undefined) return null;
    if (typeof val === "number") return val;

    let s = val.trim();
    if (!s) return null;

    s = s.replace(/^(?:Rp\.?|IDR|\$)\s*/i, "").trim();
    if (s.endsWith(",-")) {
      s = s.slice(0, -2).trim();
    }
    s = s.replace(/\s+/g, "");

    if (/^-?\d{1,3}(?:\.\d{3})+,\d+$/.test(s)) {
      s = s.replace(/\./g, "").replace(",", ".");
    } else if (/^-?\d{1,3}(?:,\d{3})+\.\d+$/.test(s)) {
      s = s.replace(/,/g, "");
    } else if (/^-?\d{1,3}(?:\.\d{3}){2,}$/.test(s)) {
      s = s.replace(/\./g, "");
    } else if (/^-?[1-9]\d{0,2}\.\d{3}$/.test(s)) {
      s = s.replace(/\./g, "");
    } else if (/^-?\d{1,3}(?:,\d{3}){2,}$/.test(s)) {
      s = s.replace(/,/g, "");
    } else if (/^-?[1-9]\d{0,2},\d{3}$/.test(s)) {
      s = s.replace(/,/g, "");
    } else if (/^-?\d+,\d{1,2}$/.test(s)) {
      s = s.replace(",", ".");
    }

    return s;
  };

  const normalizeTextInput = (val: string | number | null | undefined): string | null => {
    if (val === null || val === undefined) return null;
    const s = String(val).trim();
    return s ? s : null;
  };

  const calculateLineItemAmount = (
    qtyVal: string | number | null | undefined,
    priceVal: string | number | null | undefined
  ): string | null => {
    const normQty = normalizeMonetaryInput(qtyVal);
    const normPrice = normalizeMonetaryInput(priceVal);
    if (normQty === null || normQty === "" || normPrice === null || normPrice === "") {
      return null;
    }
    const qtyNum = Number(normQty);
    const priceNum = Number(normPrice);
    if (!Number.isFinite(qtyNum) || !Number.isFinite(priceNum)) {
      return null;
    }
    const product = Math.round((qtyNum * priceNum + Number.EPSILON) * 100) / 100;
    return String(product);
  };

  const handleAddLineItem = () => {
    setLineItems(prev => [
      ...prev,
      {
        localId: `new-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        id: null,
        description: "",
        quantity: "",
        unit_price: "",
        amount: "",
      },
    ]);
    setIsLineItemsDirty(true);
    setSaveSuccess(false);
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems(prev => prev.filter((_, idx) => idx !== index));
    setIsLineItemsDirty(true);
    setSaveSuccess(false);
  };

  const handleLineItemChange = (
    index: number,
    field: "description" | "quantity" | "unit_price" | "amount",
    value: string
  ) => {
    setLineItems(prev =>
      prev.map((item, idx) => {
        if (idx !== index) return item;
        const updatedItem: EditableLineItem = {
          ...item,
          [field]: value,
        };
        if (field === "quantity" || field === "unit_price") {
          const nextQty = field === "quantity" ? value : item.quantity;
          const nextPrice = field === "unit_price" ? value : item.unit_price;
          const autoAmount = calculateLineItemAmount(nextQty, nextPrice);
          updatedItem.amount = autoAmount ?? "";
        }
        return updatedItem;
      })
    );
    setIsLineItemsDirty(true);
    setSaveSuccess(false);
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError(null);

      const payload: InvoiceUpdatePayload = {
        vendor_name: normalizeTextInput(formData.vendor_name),
        invoice_number: normalizeTextInput(formData.invoice_number),
        invoice_date: normalizeTextInput(formData.invoice_date),
        due_date: normalizeTextInput(formData.due_date),
        subtotal: normalizeMonetaryInput(formData.subtotal),
        tax: normalizeMonetaryInput(formData.tax),
        total: normalizeMonetaryInput(formData.total),
      };

      if (isLineItemsDirty) {
        payload.line_items =
          lineItems.length > 0
            ? lineItems.map((item): InvoiceLineItemUpdatePayload => ({
                ...(item.id ? { id: item.id } : {}),
                description: normalizeTextInput(item.description) ?? "",
                quantity: normalizeMonetaryInput(item.quantity),
                unit_price: normalizeMonetaryInput(item.unit_price),
                amount: normalizeMonetaryInput(item.amount),
              }))
            : [];
      }

      const updated = await apiClient.updateInvoice(id, payload);
      setInvoice(updated);
      setFormData({
        vendor_name: updated.vendor_name || "",
        invoice_number: updated.invoice_number || "",
        invoice_date: updated.invoice_date || "",
        due_date: updated.due_date || "",
        subtotal: updated.subtotal !== null ? updated.subtotal : "",
        tax: updated.tax !== null ? updated.tax : "",
        total: updated.total !== null ? updated.total : "",
      });
      if (Array.isArray(updated.line_items)) {
        setLineItems(mapApiLineItemsToEditable(updated.line_items));
      }
      setIsLineItemsDirty(false);
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
                        type="text" inputMode="decimal" name="subtotal"
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
                        type="text" inputMode="decimal" name="tax"
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
                        type="text" inputMode="decimal" name="total"
                        value={formData.total ?? ''} onChange={handleInputChange}
                        className="block w-full rounded-md border-gray-300 pl-3 pr-12 focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border font-bold"
                        disabled={isProcessing}
                        placeholder="—"
                      />
                    </div>
                  </div>
                </div>

                {/* Line Items - Editable */}
                <div className="flex justify-between items-center border-b pb-2 pt-4">
                  <h3 className="text-md font-medium text-gray-900">Line Items</h3>
                  <button
                    type="button"
                    onClick={handleAddLineItem}
                    disabled={isProcessing || isSaving}
                    className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                  >
                    + Add Item
                  </button>
                </div>
                <div className="bg-white rounded-md border border-gray-200 overflow-x-auto shadow-sm">
                   <table className="min-w-full divide-y divide-gray-200 text-sm">
                     <thead className="bg-gray-50">
                       <tr>
                         <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                         <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase w-24">Qty</th>
                         <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase w-32">Unit Price</th>
                         <th className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase w-32">Amount</th>
                         <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase w-20">Actions</th>
                       </tr>
                     </thead>
                     <tbody className="divide-y divide-gray-200">
                        {lineItems.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                              {isProcessing ? "Extracting line items..." : "No line items found."}
                            </td>
                          </tr>
                        ) : (
                          lineItems.map((item, idx) => (
                            <tr key={item.localId} className="hover:bg-gray-50">
                              <td className="px-3 py-2 text-gray-900">
                                <span className="sr-only">{item.description}</span>
                                <input
                                  type="text"
                                  name={`line_items.${idx}.description`}
                                  aria-label={`Line item ${idx + 1} description`}
                                  value={item.description ?? ""}
                                  onChange={e => handleLineItemChange(idx, "description", e.target.value)}
                                  disabled={isProcessing || isSaving}
                                  placeholder="Description"
                                  className="block w-full min-w-[140px] rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-1.5 border text-gray-900"
                                />
                              </td>
                              <td className="px-3 py-2 text-gray-500 text-right">
                                <input
                                  type="text"
                                  inputMode="decimal"
                                  name={`line_items.${idx}.quantity`}
                                  aria-label={`Line item ${idx + 1} quantity`}
                                  value={item.quantity ?? ""}
                                  onChange={e => handleLineItemChange(idx, "quantity", e.target.value)}
                                  disabled={isProcessing || isSaving}
                                  placeholder="—"
                                  className="block w-20 ml-auto rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-1.5 border text-right text-gray-900"
                                />
                              </td>
                              <td className="px-3 py-2 text-gray-500 text-right">
                                <input
                                  type="text"
                                  inputMode="decimal"
                                  name={`line_items.${idx}.unit_price`}
                                  aria-label={`Line item ${idx + 1} unit price`}
                                  value={item.unit_price ?? ""}
                                  onChange={e => handleLineItemChange(idx, "unit_price", e.target.value)}
                                  disabled={isProcessing || isSaving}
                                  placeholder="—"
                                  className="block w-28 ml-auto rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-1.5 border text-right text-gray-900"
                                />
                              </td>
                              <td className="px-3 py-2 font-medium text-gray-900 text-right">
                                <input
                                  type="text"
                                  inputMode="decimal"
                                  name={`line_items.${idx}.amount`}
                                  aria-label={`Line item ${idx + 1} amount`}
                                  value={item.amount ?? ""}
                                  onChange={e => handleLineItemChange(idx, "amount", e.target.value)}
                                  disabled={isProcessing || isSaving}
                                  placeholder="—"
                                  className="block w-28 ml-auto rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-1.5 border text-right font-medium text-gray-900"
                                />
                              </td>
                              <td className="px-3 py-2 text-center">
                                <button
                                  type="button"
                                  onClick={() => handleRemoveLineItem(idx)}
                                  disabled={isProcessing || isSaving}
                                  aria-label={`Remove line item ${idx + 1}`}
                                  className="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 disabled:opacity-50 transition-colors"
                                >
                                  Remove
                                </button>
                              </td>
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
