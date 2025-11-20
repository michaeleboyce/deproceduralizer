"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Minimal Header - Only on Homepage */}
      <header className="border-b border-slate-200/50 bg-white/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-end gap-6">
          <Link
            href="/browse"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Browse →
          </Link>
          <Link
            href="/reporting"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Reports →
          </Link>
          <Link
            href="/anachronisms"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Anachronisms →
          </Link>
          <Link
            href="/pahlka-implementations"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Implementation →
          </Link>
          <Link
            href="/dashboard/conflicts"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Analysis →
          </Link>
          <Link
            href="/search"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
          >
            Advanced Search →
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <h1 className="text-6xl font-bold text-slate-900 mb-6 tracking-tight">
            Deproceduralizer
          </h1>
          <p className="text-2xl text-slate-600 mb-3 font-light">
            Search and analyze Washington, D.C. legal code
          </p>
          <p className="text-sm text-slate-500">
            Full-text search • Cross-references • Obligations tracking
          </p>
        </div>

        {/* Quick Search */}
        <div className="max-w-3xl mx-auto mb-20">
          <form onSubmit={handleSearch} className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search DC Code (e.g., 'notice', 'board', 'election')..."
              className="flex-1 px-6 py-5 border border-slate-300 rounded-lg text-lg
                         focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent
                         shadow-sm text-slate-900 placeholder:text-slate-400 bg-white
                         transition-all"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className="px-10 py-5 bg-teal-700 text-white rounded-lg hover:bg-teal-800
                         disabled:bg-slate-400 disabled:cursor-not-allowed
                         font-semibold text-lg shadow-sm transition-all"
            >
              Search
            </button>
          </form>
          <div className="mt-4 text-center">
            <Link
              href="/search"
              className="text-teal-700 hover:text-teal-800 text-sm font-medium transition-colors"
            >
              Or go to advanced search →
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="font-semibold text-slate-900 mb-3 text-xl">
              Full-Text Search
            </h3>
            <p className="text-slate-600 leading-relaxed">
              Powerful PostgreSQL full-text search across all DC Code sections
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
            <div className="text-4xl mb-4">🔗</div>
            <h3 className="font-semibold text-slate-900 mb-3 text-xl">
              Cross-References
            </h3>
            <p className="text-slate-600 leading-relaxed">
              Navigate relationships between code sections automatically
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
            <div className="text-4xl mb-4">📋</div>
            <h3 className="font-semibold text-slate-900 mb-3 text-xl">
              Obligations Tracking
            </h3>
            <p className="text-slate-600 leading-relaxed">
              Extract deadlines, reporting requirements, and dollar amounts
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="bg-gradient-to-br from-slate-50/50 to-white rounded-xl border border-slate-200 shadow-sm p-10 mb-16">
          <h3 className="text-xl font-semibold text-slate-900 mb-8 text-center">
            Current Database
          </h3>
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">100</div>
              <div className="text-sm text-slate-600 font-medium">Sections</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">2</div>
              <div className="text-sm text-slate-600 font-medium">Titles</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">100%</div>
              <div className="text-sm text-slate-600 font-medium">FTS Indexed</div>
            </div>
          </div>
          <p className="text-xs text-slate-500 text-center mt-8 px-4">
            Currently loaded: DC Code Titles 1-2 (subset for development)
          </p>
        </div>

        {/* About */}
        <div className="text-center">
          <p className="text-slate-600 max-w-2xl mx-auto leading-relaxed text-lg">
            The Deproceduralizer makes DC legal code more accessible through
            modern search technology, semantic analysis, and automated
            extraction of key obligations and requirements.
          </p>
        </div>
      </div>
    </div>
  );
}
