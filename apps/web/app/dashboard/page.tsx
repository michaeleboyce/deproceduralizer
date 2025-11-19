import Navigation from "@/components/Navigation";
import Link from "next/link";
import { AlertTriangle, FileText, Search, BarChart } from "lucide-react";

export default function DashboardPage() {
  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Dashboard", href: "/dashboard" }
      ]} />
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Dashboard</h1>
            <p className="text-slate-600">
              Overview of legislative analysis, reporting requirements, and system status.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Analysis Card */}
            <Link href="/dashboard/conflicts" className="block group">
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm hover:shadow-md hover:border-teal-200 transition-all h-full">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 bg-amber-50 rounded-lg group-hover:bg-amber-100 transition-colors">
                    <AlertTriangle className="w-6 h-6 text-amber-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">Legislative Analysis</h2>
                </div>
                <p className="text-slate-600 mb-4">
                  Review potential conflicts, duplicates, and inconsistencies identified by AI analysis across the legal code.
                </p>
                <span className="text-teal-700 font-medium text-sm group-hover:underline">
                  View Analysis →
                </span>
              </div>
            </Link>

            {/* Reporting Card */}
            <Link href="/reporting" className="block group">
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm hover:shadow-md hover:border-teal-200 transition-all h-full">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
                    <FileText className="w-6 h-6 text-blue-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">Reporting Requirements</h2>
                </div>
                <p className="text-slate-600 mb-4">
                  Browse and filter extracted reporting obligations, deadlines, and compliance requirements.
                </p>
                <span className="text-teal-700 font-medium text-sm group-hover:underline">
                  View Reports →
                </span>
              </div>
            </Link>

            {/* Search Card */}
            <Link href="/search" className="block group">
              <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm hover:shadow-md hover:border-teal-200 transition-all h-full">
                <div className="flex items-center gap-4 mb-4">
                  <div className="p-3 bg-purple-50 rounded-lg group-hover:bg-purple-100 transition-colors">
                    <Search className="w-6 h-6 text-purple-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">Advanced Search</h2>
                </div>
                <p className="text-slate-600 mb-4">
                  Perform full-text and semantic searches across the entire legal corpus with advanced filtering.
                </p>
                <span className="text-teal-700 font-medium text-sm group-hover:underline">
                  Go to Search →
                </span>
              </div>
            </Link>

            {/* System Status (Placeholder) */}
            <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 border-dashed h-full opacity-75">
              <div className="flex items-center gap-4 mb-4">
                <div className="p-3 bg-slate-100 rounded-lg">
                  <BarChart className="w-6 h-6 text-slate-400" />
                </div>
                <h2 className="text-xl font-semibold text-slate-500">System Metrics</h2>
              </div>
              <p className="text-slate-500 mb-4">
                Database statistics, indexing status, and pipeline performance metrics.
              </p>
              <span className="text-slate-400 text-sm font-medium cursor-not-allowed">
                Coming Soon
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
