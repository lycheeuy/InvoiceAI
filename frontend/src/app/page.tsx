"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { HealthResponse, InvoiceListItem } from "@/types/api";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [totalInvoices, setTotalInvoices] = useState<number | null>(null);
  const [totalProcessed, setTotalProcessed] = useState<number | null>(null);
  const [pendingReview, setPendingReview] = useState<number | null>(null);
  const [totalFailures, setTotalFailures] = useState<number | null>(null);
  
  const [recentInvoices, setRecentInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [
        healthData, 
        recentData, 
        processedData, 
        reviewData, 
        failedData
      ] = await Promise.all([
        apiClient.getHealth(),
        apiClient.getInvoices(1, 5),
        apiClient.getInvoices(1, 1, 'PROCESSED'),
        apiClient.getInvoices(1, 1, 'NEEDS_REVIEW'),
        apiClient.getInvoices(1, 1, 'FAILED')
      ]);
      
      setHealth(healthData);
      setTotalInvoices(recentData.total);
      setRecentInvoices(recentData.items);
      
      setTotalProcessed(processedData.total);
      setPendingReview(reviewData.total);
      setTotalFailures(failedData.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !recentInvoices.length) {
    return <LoadingState message="Loading dashboard insights..." />;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">Overview of your invoice processing pipeline.</p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link 
            href="/upload" 
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Upload New Invoice
          </Link>
        </div>
      </div>
      
      {error && <ErrorState message={error} retry={fetchData} />}

      {/* KPI METRIC CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6 flex flex-col justify-between">
          <h2 className="text-sm font-medium text-gray-500 mb-1 uppercase tracking-wider">Total Invoices</h2>
          <p className="text-3xl font-bold text-gray-900">
            {totalInvoices !== null ? totalInvoices : '—'}
          </p>
        </Card>
        <Card className="p-6 flex flex-col justify-between">
          <h2 className="text-sm font-medium text-gray-500 mb-1 uppercase tracking-wider">Total Processed</h2>
          <p className="text-3xl font-bold text-green-600">
            {totalProcessed !== null ? totalProcessed : '—'}
          </p>
        </Card>
        <Card className="p-6 flex flex-col justify-between">
          <h2 className="text-sm font-medium text-gray-500 mb-1 uppercase tracking-wider">Pending Review</h2>
          <p className="text-3xl font-bold text-yellow-600">
            {pendingReview !== null ? pendingReview : '—'}
          </p>
        </Card>
        <Card className="p-6 flex flex-col justify-between">
          <h2 className="text-sm font-medium text-gray-500 mb-1 uppercase tracking-wider">Failures</h2>
          <p className="text-3xl font-bold text-red-600">
            {totalFailures !== null ? totalFailures : '—'}
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <div className="px-4 py-5 sm:px-6 flex justify-between items-center border-b border-gray-200 bg-white">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Recent Invoices
            </h3>
            <Link href="/invoices" className="text-sm font-medium text-blue-600 hover:text-blue-500">
              View all &rarr;
            </Link>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">Vendor</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="relative px-6 py-3"><span className="sr-only">View</span></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recentInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-6">
                      <EmptyState 
                        title="No recent invoices" 
                        description="You haven't uploaded any invoices yet."
                      />
                    </td>
                  </tr>
                ) : (
                  recentInvoices.map((invoice) => (
                    <tr key={invoice.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-[150px] sm:max-w-xs" title={invoice.file_name}>{invoice.file_name}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{new Date(invoice.created_at).toLocaleDateString()}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 hidden sm:table-cell">
                        {invoice.vendor_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={invoice.status} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <Link href={`/invoices/${invoice.id}`} className="text-blue-600 hover:text-blue-900">
                          View<span className="sr-only">, {invoice.file_name}</span>
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* System Status Sidebar Widget */}
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4 border-b pb-2">System Health</h2>
            <div className="flex items-center space-x-3 mb-4">
              <span className={`flex h-3 w-3 relative`}>
                {health?.status === 'healthy' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-3 w-3 ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`}></span>
              </span>
              <span className="text-sm text-gray-700 font-medium">API Connection</span>
            </div>
            <div className="flex items-center space-x-3">
               <span className={`flex h-3 w-3 relative`}>
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${health?.database === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></span>
               </span>
               <span className="text-sm text-gray-700 font-medium">Database Connection</span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
