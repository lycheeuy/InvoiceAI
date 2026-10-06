"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api";
import { InvoiceUploadResponse } from "@/types/api";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvoiceUploadResponse | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds the 10MB maximum size limit.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.uploadInvoice(file);
      setResult(res);
      setFile(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred during upload.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Invoice</h1>
        <p className="mt-1 text-sm text-gray-500">Select a PDF, PNG, or JPEG file to begin extraction.</p>
      </div>

      {error && <ErrorState message={error} />}

      {result && (
        <div className="bg-green-50 border border-green-200 p-6 rounded-lg shadow-sm">
          <div className="flex items-center">
            <svg className="h-6 w-6 text-green-600 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="font-semibold text-green-900 text-lg">Upload Successful</h3>
          </div>
          <div className="mt-4 text-sm text-green-800 space-y-2">
            <p>Your document has been secured and queued for AI extraction.</p>
            <div className="bg-white/50 rounded p-3 mt-3 flex flex-col sm:flex-row sm:items-center justify-between">
              <div className="truncate pr-4 font-medium" title={result.file_name}>{result.file_name}</div>
              <div className="mt-2 sm:mt-0 flex-shrink-0"><StatusBadge status={result.status} /></div>
            </div>
          </div>
          <div className="mt-6">
            <Link 
              href={`/invoices/${result.id}`} 
              className="w-full sm:w-auto inline-flex justify-center items-center py-2 px-6 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
            >
              View Document Details &rarr;
            </Link>
          </div>
        </div>
      )}

      <Card className="p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Document File
            </label>
            <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-blue-400 transition-colors bg-gray-50">
              <div className="space-y-1 text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                  <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div className="flex text-sm text-gray-600 justify-center mt-2">
                  <label htmlFor="file-upload" className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500 p-1">
                    <span>Upload a file</span>
                    <input id="file-upload" name="file-upload" type="file" className="sr-only" accept=".pdf,.png,.jpg,.jpeg" onChange={handleFileChange} disabled={loading} />
                  </label>
                  <p className="pl-1 py-1">or drag and drop</p>
                </div>
                <p className="text-xs text-gray-500 mt-2">PDF, PNG, JPG up to 10MB</p>
              </div>
            </div>
          </div>
          
          {file && (
             <div className="bg-blue-50 border border-blue-100 rounded-md p-3 flex items-center justify-between">
                <span className="text-sm font-medium text-blue-800 truncate">{file.name}</span>
                <span className="text-xs text-blue-600 ml-4 whitespace-nowrap">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
             </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={!file || loading}
              className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading && <Spinner className="mr-2 h-4 w-4 text-white" />}
              {loading ? "Uploading & Queuing..." : "Upload Invoice"}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
