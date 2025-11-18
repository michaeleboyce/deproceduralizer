"use client";

import { useState, FormEvent, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import Navigation from "@/components/Navigation";

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

function SearchPageContent() {
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
  const [hasReporting, setHasReporting] = useState(false);
  const [hasSimilar, setHasSimilar] = useState(false);
  const [minSimilarity, setMinSimilarity] = useState(70);
  const [maxSimilarity, setMaxSimilarity] = useState(100);
  const [similarityClassification, setSimilarityClassification] = useState("");
  const [showLegend, setShowLegend] = useState(false);
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
    const urlHasReporting = searchParams.get("hasReporting") === "true";
    const urlHasSimilar = searchParams.get("hasSimilar") === "true";
    const urlMinSimilarity = parseInt(searchParams.get("minSimilarity") || "70", 10);
    const urlMaxSimilarity = parseInt(searchParams.get("maxSimilarity") || "100", 10);
    const urlSimilarityClassification = searchParams.get("similarityClassification") || "";
    const urlPage = parseInt(searchParams.get("page") || "1", 10);

    if (urlQuery || urlTitle || urlChapter || urlHasReporting || urlHasSimilar || urlSimilarityClassification) {
      setQuery(urlQuery);
      setSelectedTitle(urlTitle);
      setSelectedChapter(urlChapter);
      setHasReporting(urlHasReporting);
      setHasSimilar(urlHasSimilar);
      setMinSimilarity(urlMinSimilarity);
      setMaxSimilarity(urlMaxSimilarity);
      setSimilarityClassification(urlSimilarityClassification);
      setCurrentPage(urlPage);
      performSearch(urlQuery, urlTitle, urlChapter, urlHasReporting, urlHasSimilar, urlMinSimilarity, urlMaxSimilarity, urlSimilarityClassification, urlPage);
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
    reporting: boolean = hasReporting,
    similar: boolean = hasSimilar,
    minSim: number = minSimilarity,
    maxSim: number = maxSimilarity,
    simClassification: string = similarityClassification,
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
      if (reporting) params.append("hasReporting", "true");
      if (similar) params.append("hasSimilar", "true");
      if (similar && minSim > 70) params.append("minSimilarity", (minSim / 100).toString());
      if (similar && maxSim < 100) params.append("maxSimilarity", (maxSim / 100).toString());
      if (simClassification) params.append("similarityClassification", simClassification);
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
    updateURL(query, selectedTitle, selectedChapter, hasReporting, hasSimilar, minSimilarity, maxSimilarity, similarityClassification, 1);
  };

  const handleFilterChange = () => {
    setCurrentPage(1);
    updateURL(query, selectedTitle, selectedChapter, hasReporting, hasSimilar, minSimilarity, maxSimilarity, similarityClassification, 1);
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    updateURL(query, selectedTitle, selectedChapter, hasReporting, hasSimilar, minSimilarity, maxSimilarity, similarityClassification, newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const updateURL = (q: string, title: string, chapter: string, reporting: boolean, similar: boolean, minSim: number, maxSim: number, simClass: string, page: number) => {
    const params = new URLSearchParams();
    if (q.trim()) params.append("q", q);
    if (title) params.append("title", title);
    if (chapter) params.append("chapter", chapter);
    if (reporting) params.append("hasReporting", "true");
    if (similar) params.append("hasSimilar", "true");
    if (similar && minSim > 70) params.append("minSimilarity", minSim.toString());
    if (similar && maxSim < 100) params.append("maxSimilarity", maxSim.toString());
    if (simClass) params.append("similarityClassification", simClass);
    if (page > 1) params.append("page", page.toString());

    router.push(`/search?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedTitle("");
    setSelectedChapter("");
    setHasReporting(false);
    setHasSimilar(false);
    setMinSimilarity(70);
    setMaxSimilarity(100);
    setSimilarityClassification("");
    setCurrentPage(1);
    updateURL(query, "", "", false, false, 70, 100, "", 1);
  };

  const hasActiveFilters = selectedTitle || selectedChapter || hasReporting || hasSimilar || similarityClassification;

  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Search" }
      ]} />
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 mb-2">
              DC Code Search
            </h1>
            <p className="text-slate-600">
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
                className="flex-1 px-4 py-3 border border-slate-300 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent
                           text-slate-900 placeholder:text-slate-400"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 bg-teal-700 text-white rounded-lg hover:bg-teal-800
                           disabled:bg-slate-400 disabled:cursor-not-allowed
                           font-medium transition-colors shadow-sm"
              >
                {loading ? "Searching..." : "Search"}
              </button>
            </div>
          </form>

          {/* Filters */}
          <div className="mb-6 bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Title
                </label>
                <select
                  value={selectedTitle}
                  onChange={(e) => {
                    setSelectedTitle(e.target.value);
                    setSelectedChapter("");
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg
                             focus:outline-none focus:ring-2 focus:ring-teal-500
                             text-slate-900 bg-white"
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
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Chapter
                </label>
                <select
                  value={selectedChapter}
                  onChange={(e) => setSelectedChapter(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg
                             focus:outline-none focus:ring-2 focus:ring-teal-500
                             text-slate-900 bg-white disabled:bg-slate-100"
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

              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasReporting}
                    onChange={(e) => setHasReporting(e.target.checked)}
                    disabled={loading}
                    className="w-4 h-4 text-teal-700 border-slate-300 rounded
                               focus:ring-teal-500"
                  />
                  <span className="text-sm font-medium text-slate-700">
                    Has reporting requirement
                  </span>
                </label>
              </div>
            </div>

            {/* Similarity Filters Row */}
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hasSimilar}
                      onChange={(e) => setHasSimilar(e.target.checked)}
                      disabled={loading}
                      className="w-4 h-4 text-teal-700 border-slate-300 rounded
                                 focus:ring-teal-500"
                    />
                    <span className="text-sm font-medium text-slate-700">
                      Has similar sections
                    </span>
                  </label>
                </div>

                {hasSimilar && (
                  <>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-slate-700">
                        Similarity:
                      </label>
                      <input
                        type="range"
                        min="70"
                        max="100"
                        value={minSimilarity}
                        onChange={(e) => setMinSimilarity(parseInt(e.target.value))}
                        disabled={loading}
                        className="w-24"
                      />
                      <span className="text-sm text-slate-600 font-mono">
                        {minSimilarity}%
                      </span>
                      <span className="text-slate-400">to</span>
                      <input
                        type="range"
                        min="70"
                        max="100"
                        value={maxSimilarity}
                        onChange={(e) => setMaxSimilarity(parseInt(e.target.value))}
                        disabled={loading}
                        className="w-24"
                      />
                      <span className="text-sm text-slate-600 font-mono">
                        {maxSimilarity}%
                      </span>
                    </div>

                    <div className="flex-1 min-w-[180px]">
                      <select
                        value={similarityClassification}
                        onChange={(e) => setSimilarityClassification(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg
                                   focus:outline-none focus:ring-2 focus:ring-teal-500
                                   text-slate-900 bg-white text-sm"
                        disabled={loading}
                      >
                        <option value="">All Classifications</option>
                        <option value="related">Related</option>
                        <option value="duplicate">Duplicate</option>
                        <option value="superseded">Superseded</option>
                        <option value="conflicting">Conflicting</option>
                        <option value="unrelated">Unrelated</option>
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={() => setShowLegend(!showLegend)}
                      className="text-sm text-teal-700 hover:text-teal-800 font-medium
                                 flex items-center gap-1"
                    >
                      <span className="text-lg">ℹ️</span>
                      {showLegend ? "Hide" : "Show"} Legend
                    </button>
                  </>
                )}
              </div>

              {/* Classification Legend */}
              {hasSimilar && showLegend && (
                <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <h4 className="font-semibold text-slate-900 mb-3 text-sm">
                    Classification Types:
                  </h4>
                  <dl className="space-y-2 text-sm">
                    <div className="flex gap-2">
                      <dt className="font-semibold text-emerald-700 min-w-[100px]">Related:</dt>
                      <dd className="text-slate-600">
                        Similar topics but serve different purposes
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-semibold text-amber-700 min-w-[100px]">Duplicate:</dt>
                      <dd className="text-slate-600">
                        Nearly identical provisions, potential for consolidation
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-semibold text-sky-700 min-w-[100px]">Superseded:</dt>
                      <dd className="text-slate-600">
                        One section replaces or updates the other
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-semibold text-red-700 min-w-[100px]">Conflicting:</dt>
                      <dd className="text-slate-600">
                        Similar language but contradictory requirements
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-semibold text-slate-600 min-w-[100px]">Unrelated:</dt>
                      <dd className="text-slate-600">
                        High similarity score but not actually related
                      </dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>

            <div className="flex gap-2 items-end mt-4">
                <button
                  type="button"
                  onClick={handleFilterChange}
                  disabled={loading}
                  className="px-4 py-2 bg-teal-700 text-white rounded-lg hover:bg-teal-800
                             disabled:bg-slate-400 font-medium transition-colors"
                >
                  Apply Filters
                </button>
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    disabled={loading}
                    className="px-4 py-2 text-slate-600 hover:text-slate-900
                               font-medium transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>

            {/* Active Filters Display */}
            {hasActiveFilters && (
              <div className="mt-4 pt-4 border-t border-slate-200 flex gap-2 flex-wrap">
                {selectedTitle && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1
                                   bg-sky-100 text-sky-800 rounded-full text-sm font-medium">
                    {selectedTitle}
                    <button
                      onClick={() => {
                        setSelectedTitle("");
                        setSelectedChapter("");
                      }}
                      className="hover:text-sky-900 text-lg leading-none"
                    >
                      ×
                    </button>
                  </span>
                )}
                {selectedChapter && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1
                                   bg-sky-100 text-sky-800 rounded-full text-sm font-medium">
                    {selectedChapter}
                    <button
                      onClick={() => setSelectedChapter("")}
                      className="hover:text-sky-900 text-lg leading-none"
                    >
                      ×
                    </button>
                  </span>
                )}
                {hasReporting && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1
                                   bg-violet-100 text-violet-800 rounded-full text-sm font-medium">
                    Has Reporting
                    <button
                      onClick={() => setHasReporting(false)}
                      className="hover:text-violet-900 text-lg leading-none"
                    >
                      ×
                    </button>
                  </span>
                )}
                {hasSimilar && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1
                                   bg-teal-100 text-teal-800 rounded-full text-sm font-medium">
                    Has Similar ({minSimilarity}-{maxSimilarity}%)
                    <button
                      onClick={() => {
                        setHasSimilar(false);
                        setMinSimilarity(70);
                        setMaxSimilarity(100);
                      }}
                      className="hover:text-teal-900 text-lg leading-none"
                    >
                      ×
                    </button>
                  </span>
                )}
                {similarityClassification && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1
                                   bg-emerald-100 text-emerald-800 rounded-full text-sm font-medium capitalize">
                    {similarityClassification}
                    <button
                      onClick={() => setSimilarityClassification("")}
                      className="hover:text-emerald-900 text-lg leading-none"
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
              <div className="mb-4 text-slate-600 font-medium">
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
                <div className="text-center py-16 bg-white rounded-lg border border-slate-200">
                  <p className="text-slate-500 text-lg font-medium">No results found</p>
                  <p className="text-slate-400 text-sm mt-2">
                    Try different keywords or filters
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-3 mb-6">
                    {results.map((result) => (
                      <Link
                        key={result.id}
                        href={`/section/${result.id}`}
                        className="block bg-white p-5 rounded-lg border border-slate-200
                                   hover:border-teal-300 hover:shadow-md transition-all"
                      >
                        <div className="flex items-center gap-2 mb-2 text-xs text-slate-500">
                          <span>{result.titleLabel}</span>
                          <span className="text-slate-400">›</span>
                          <span>{result.chapterLabel}</span>
                          <span className="text-slate-400">›</span>
                          <span className="font-mono font-medium text-teal-700">
                            {result.citation}
                          </span>
                        </div>

                        <h2 className="text-lg font-semibold text-slate-900 mb-2">
                          {result.heading}
                        </h2>

                        <p className="text-slate-600 text-sm line-clamp-2 leading-relaxed">
                          {result.snippet}
                          {result.snippet.length >= 200 && "..."}
                        </p>
                      </Link>
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-3">
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                        className="px-4 py-2 border border-slate-300 rounded-lg
                                   hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed
                                   text-slate-900 font-medium transition-colors"
                      >
                        Previous
                      </button>
                      <span className="px-4 py-2 text-slate-600 font-medium">
                        Page {currentPage} of {totalPages}
                      </span>
                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                        className="px-4 py-2 border border-slate-300 rounded-lg
                                   hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed
                                   text-slate-900 font-medium transition-colors"
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
            <div className="text-center py-16 bg-white rounded-lg border border-slate-200">
              <p className="text-slate-400">
                Enter a search term or select filters to find DC Code sections
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <p className="text-slate-500">Loading search...</p>
          </div>
        </div>
      </div>
    }>
      <SearchPageContent />
    </Suspense>
  );
}
