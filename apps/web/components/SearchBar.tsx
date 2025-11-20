"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <>
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
    </>
  );
}
