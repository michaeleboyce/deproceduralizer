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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-teal-50/30">
      {/* Minimal Header - Only on Homepage */}
      <header className="border-b border-slate-200/50 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="text-lg font-bold text-slate-900 hover:text-teal-700 transition-colors"
          >
            Deproceduralizer
          </Link>
          <div className="flex gap-6">
            <Link
              href="/search"
              className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Search
            </Link>
            <Link
              href="/browse"
              className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Browse
            </Link>
            <Link
              href="/dashboard/conflicts"
              className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            >
              Analysis
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-6xl mx-auto px-4 py-20 md:py-32">
        <div className="text-center mb-12">
          <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold text-slate-900 mb-6 tracking-tight leading-none">
            Deproceduralizer
          </h1>
          <p className="text-2xl md:text-3xl text-slate-600 mb-4 font-light">
            Search and analyze Washington, D.C. legal code
          </p>
          <p className="text-base text-slate-500">
            Full-text search • Cross-references • Obligations tracking
          </p>
        </div>

        {/* Enhanced Search Bar */}
        <div className="max-w-4xl mx-auto mb-24">
          <form onSubmit={handleSearch} className="relative">
            <div className="flex gap-3 shadow-xl rounded-xl overflow-hidden border border-slate-200 bg-white">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search DC Code (e.g., 'notice', 'board', 'election')..."
                className="flex-1 px-6 py-6 text-lg
                           focus:outline-none
                           text-slate-900 placeholder:text-slate-400 bg-white"
              />
              <button
                type="submit"
                disabled={!query.trim()}
                className="px-12 py-6 bg-teal-700 text-white hover:bg-teal-800
                           disabled:bg-slate-400 disabled:cursor-not-allowed
                           font-semibold text-lg transition-colors"
              >
                Search
              </button>
            </div>
          </form>
          <div className="mt-5 text-center">
            <Link
              href="/search"
              className="text-teal-700 hover:text-teal-800 text-sm font-medium transition-colors inline-flex items-center gap-1"
            >
              Advanced search options
              <span className="text-lg">→</span>
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
              <div className="text-5xl font-bold text-teal-700 mb-2">12,954</div>
              <div className="text-sm text-slate-600 font-medium">Sections</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">10</div>
              <div className="text-sm text-slate-600 font-medium">Titles</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">100%</div>
              <div className="text-sm text-slate-600 font-medium">FTS Indexed</div>
            </div>
          </div>
          <p className="text-xs text-slate-500 text-center mt-8 px-4">
            Currently loaded: DC Code Titles 1-10 (medium dataset for development)
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
