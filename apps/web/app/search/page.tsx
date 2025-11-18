"use client";

import { useState, FormEvent, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

interface SearchResult {
  id: string;
  citation: string;
  heading: string;
  snippet: string;
  titleLabel: string;
  chapterLabel: string;
}

interface SearchResponse {
  results: SearchResult[];
  query: string;
  count: number;
  total: number;
  page: number;
  totalPages: number;
  filters: {
    title: string | null;
    chapter: string | null;
  };
}

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Search state
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [availableTitles, setAvailableTitles] = useState<string[]>([]);
  const [availableChapters, setAvailableChapters] = useState<string[]>([]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalResults, setTotalResults] = useState(0);

  // Load filter options on mount
  useEffect(() => {
    loadTitles();
  }, []);

  // Load chapters when title changes
  useEffect(() => {
    if (selectedTitle) {
      loadChapters(selectedTitle);
    } else {
      setAvailableChapters([]);
      setSelectedChapter("");
    }
  }, [selectedTitle]);

  // Auto-search from URL params
  useEffect(() => {
    const urlQuery = searchParams.get("q") || searchParams.get("query") || "";
    const urlTitle = searchParams.get("title") || "";
    const urlChapter = searchParams.get("chapter") || "";
    const urlPage = parseInt(searchParams.get("page") || "1", 10);

    if (urlQuery || urlTitle || urlChapter) {
      setQuery(urlQuery);
      setSelectedTitle(urlTitle);
      setSelectedChapter(urlChapter);
      setCurrentPage(urlPage);
      performSearch(urlQuery, urlTitle, urlChapter, urlPage);
    }
  }, [searchParams]);

  const loadTitles = async () => {
    try {
      const response = await fetch("/api/filters/titles");
      const data = await response.json();
      setAvailableTitles(data.titles || []);
    } catch (err) {
      console.error("Failed to load titles:", err);
    }
  };

  const loadChapters = async (title: string) => {
    try {
      const response = await fetch(
        `/api/filters/chapters?title=${encodeURIComponent(title)}`
      );
      const data = await response.json();
      setAvailableChapters(data.chapters || []);
    } catch (err) {
      console.error("Failed to load chapters:", err);
    }
  };

  const performSearch = async (
    searchQuery: string,
    title: string = selectedTitle,
    chapter: string = selectedChapter,
    page: number = currentPage
  ) => {
    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append("query", searchQuery);
      if (title) params.append("title", title);
      if (chapter) params.append("chapter", chapter);
      params.append("page", page.toString());

      const response = await fetch(`/api/search?${params.toString()}`);

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const data: SearchResponse = await response.json();
      setResults(data.results);
      setTotalResults(data.total);
      setTotalPages(data.totalPages);
      setCurrentPage(data.page);
    } catch (err) {
      setError("Failed to search. Please try again.");
      console.error("Search error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    updateURL(query, selectedTitle, selectedChapter, 1);
  };

  const handleFilterChange = () => {
    setCurrentPage(1);
    updateURL(query, selectedTitle, selectedChapter, 1);
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    updateURL(query, selectedTitle, selectedChapter, newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const updateURL = (q: string, title: string, chapter: string, page: number) => {
    const params = new URLSearchParams();
    if (q.trim()) params.append("q", q);
    if (title) params.append("title", title);
    if (chapter) params.append("chapter", chapter);
    if (page > 1) params.append("page", page.toString());

    router.push(`/search?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedTitle("");
    setSelectedChapter("");
    setCurrentPage(1);
    updateURL(query, "", "", 1);
  };

  const hasActiveFilters = selectedTitle || selectedChapter;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            DC Code Search
          </h1>
          <p className="text-gray-600">
            Search through Washington, D.C. legal code sections
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for sections (e.g., 'notice', 'board')..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </form>

        {/* Filters */}
        <div className="mb-6 bg-white p-4 rounded-lg border border-gray-200">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title
              </label>
              <select
                value={selectedTitle}
                onChange={(e) => {
                  setSelectedTitle(e.target.value);
                  setSelectedChapter("");
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                disabled={loading}
              >
                <option value="">All Titles</option>
                {availableTitles.map((title) => (
                  <option key={title} value={title}>
                    {title}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Chapter
              </label>
              <select
                value={selectedChapter}
                onChange={(e) => setSelectedChapter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 disabled:bg-gray-100"
                disabled={!selectedTitle || loading}
              >
                <option value="">All Chapters</option>
                {availableChapters.map((chapter) => (
                  <option key={chapter} value={chapter}>
                    {chapter}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2 items-end">
              <button
                type="button"
                onClick={handleFilterChange}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium transition-colors"
              >
                Apply Filters
              </button>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  disabled={loading}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className="mt-3 flex gap-2 flex-wrap">
              {selectedTitle && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                  {selectedTitle}
                  <button
                    onClick={() => {
                      setSelectedTitle("");
                      setSelectedChapter("");
                    }}
                    className="hover:text-blue-900"
                  >
                    ×
                  </button>
                </span>
              )}
              {selectedChapter && (
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                  {selectedChapter}
                  <button
                    onClick={() => setSelectedChapter("")}
                    className="hover:text-blue-900"
                  >
                    ×
                  </button>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Results */}
        {searched && !loading && (
          <div>
            <div className="mb-4 text-gray-600">
              {totalResults > 0 ? (
                <>
                  Showing {(currentPage - 1) * 20 + 1}-
                  {Math.min(currentPage * 20, totalResults)} of {totalResults}{" "}
                  result{totalResults !== 1 ? "s" : ""}
                </>
              ) : (
                "No results found"
              )}
            </div>

            {results.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <p className="text-gray-500 text-lg">No results found</p>
                <p className="text-gray-400 text-sm mt-2">
                  Try different keywords or filters
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-4 mb-6">
                  {results.map((result) => (
                    <Link
                      key={result.id}
                      href={`/section/${result.id}`}
                      className="block bg-white p-6 rounded-lg border border-gray-200 hover:border-blue-400 hover:shadow-md transition-all"
                    >
                      <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
                        <span>{result.titleLabel}</span>
                        <span>›</span>
                        <span>{result.chapterLabel}</span>
                        <span>›</span>
                        <span className="font-mono font-medium text-blue-600">
                          {result.citation}
                        </span>
                      </div>

                      <h2 className="text-xl font-semibold text-gray-900 mb-2">
                        {result.heading}
                      </h2>

                      <p className="text-gray-600 line-clamp-3">
                        {result.snippet}
                        {result.snippet.length >= 200 && "..."}
                      </p>
                    </Link>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900"
                    >
                      Previous
                    </button>
                    <span className="px-4 py-2 text-gray-600">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Initial State */}
        {!searched && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <p className="text-gray-400">
              Enter a search term or select filters to find DC Code sections
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
