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
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Hero Section */}
      <div className="max-w-5xl mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Deproceduralizer
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Search and analyze Washington, D.C. legal code
          </p>
          <p className="text-sm text-gray-500">
            Full-text search • Cross-references • Obligations tracking
          </p>
        </div>

        {/* Quick Search */}
        <div className="max-w-2xl mx-auto mb-16">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search DC Code (e.g., 'notice', 'board', 'election')..."
              className="flex-1 px-6 py-4 border border-gray-300 rounded-lg text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm text-gray-900"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium text-lg shadow-sm transition-colors"
            >
              Search
            </button>
          </form>
          <div className="mt-3 text-center">
            <Link
              href="/search"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Or go to advanced search →
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-3xl mb-3">🔍</div>
            <h3 className="font-semibold text-gray-900 mb-2">
              Full-Text Search
            </h3>
            <p className="text-gray-600 text-sm">
              Powerful PostgreSQL full-text search across all DC Code sections
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-3xl mb-3">🔗</div>
            <h3 className="font-semibold text-gray-900 mb-2">
              Cross-References
            </h3>
            <p className="text-gray-600 text-sm">
              Navigate relationships between code sections automatically
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-3xl mb-3">📋</div>
            <h3 className="font-semibold text-gray-900 mb-2">
              Obligations Tracking
            </h3>
            <p className="text-gray-600 text-sm">
              Extract deadlines, reporting requirements, and dollar amounts
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 text-center">
            Current Database
          </h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-3xl font-bold text-blue-600">100</div>
              <div className="text-sm text-gray-600 mt-1">Sections</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-600">2</div>
              <div className="text-sm text-gray-600 mt-1">Titles</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-600">100%</div>
              <div className="text-sm text-gray-600 mt-1">FTS Indexed</div>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center mt-4">
            Currently loaded: DC Code Titles 1-2 (subset for development)
          </p>
        </div>

        {/* About */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 max-w-2xl mx-auto">
            The Deproceduralizer makes DC legal code more accessible through
            modern search technology, semantic analysis, and automated
            extraction of key obligations and requirements.
          </p>
        </div>
      </div>
    </div>
  );
}
