"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navigation from "@/components/Navigation";
import { Suspense } from "react";

interface AnachronismIndicator {
  id: number;
  category: string;
  severity: string;
  modernEquivalent: string | null;
  recommendation: string;
  explanation: string;
  matchedPhrases: string[];
}

interface AnachronismSection {
  id: string;
  citation: string;
  heading: string;
  title_label: string;
  chapter_label: string;
  has_anachronism: boolean;
  overall_severity: string;
  summary: string | null;
  requires_immediate_review: boolean;
  model_used: string | null;
  analyzed_at: string;
  indicators: AnachronismIndicator[];
}

interface AnachronismResponse {
  results: AnachronismSection[];
  total: number;
  filters: {
    severity: string | null;
    category: string | null;
    title: string | null;
    chapter: string | null;
    requiresReview: boolean | null;
    searchQuery: string | null;
    sortBy: string;
  };
  allCategories: Array<{ category: string; count: number }>;
  severityDistribution: Array<{ severity: string; count: number }>;
}

function AnachronismsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [results, setResults] = useState<AnachronismSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // Filter state
  const [selectedSeverity, setSelectedSeverity] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [requiresReview, setRequiresReview] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("severity");

  // Applied filters
  const [appliedSeverity, setAppliedSeverity] = useState("");
  const [appliedCategory, setAppliedCategory] = useState("");
  const [appliedTitle, setAppliedTitle] = useState("");
  const [appliedChapter, setAppliedChapter] = useState("");
  const [appliedRequiresReview, setAppliedRequiresReview] = useState(false);
  const [appliedSearchQuery, setAppliedSearchQuery] = useState("");

  // Available options
  const [allCategories, setAllCategories] = useState<Array<{ category: string; count: number }>>([]);
  const [severityDistribution, setSeverityDistribution] = useState<Array<{ severity: string; count: number }>>([]);
  const [availableTitles, setAvailableTitles] = useState<string[]>([]);
  const [availableChapters, setAvailableChapters] = useState<string[]>([]);

  // Load titles on mount
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

  // Auto-load from URL params
  useEffect(() => {
    const urlSeverity = searchParams.get("severity") || "";
    const urlCategory = searchParams.get("category") || "";
    const urlTitle = searchParams.get("title") || "";
    const urlChapter = searchParams.get("chapter") || "";
    const urlRequiresReview = searchParams.get("requiresReview") === "true";
    const urlSearchQuery = searchParams.get("searchQuery") || "";
    const urlSortBy = searchParams.get("sortBy") || "severity";

    setSelectedSeverity(urlSeverity);
    setSelectedCategory(urlCategory);
    setSelectedTitle(urlTitle);
    setSelectedChapter(urlChapter);
    setRequiresReview(urlRequiresReview);
    setSearchQuery(urlSearchQuery);
    setSortBy(urlSortBy);

    setAppliedSeverity(urlSeverity);
    setAppliedCategory(urlCategory);
    setAppliedTitle(urlTitle);
    setAppliedChapter(urlChapter);
    setAppliedRequiresReview(urlRequiresReview);
    setAppliedSearchQuery(urlSearchQuery);

    fetchAnachronismData(urlSeverity, urlCategory, urlTitle, urlChapter, urlRequiresReview, urlSearchQuery, urlSortBy);
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
      const response = await fetch(`/api/filters/chapters?title=${encodeURIComponent(title)}`);
      const data = await response.json();
      setAvailableChapters(data.chapters || []);
    } catch (err) {
      console.error("Failed to load chapters:", err);
    }
  };

  const fetchAnachronismData = async (
    severity: string = selectedSeverity,
    category: string = selectedCategory,
    title: string = selectedTitle,
    chapter: string = selectedChapter,
    review: boolean = requiresReview,
    search: string = searchQuery,
    sort: string = sortBy
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (severity) params.append("severity", severity);
      if (category) params.append("category", category);
      if (title) params.append("title", title);
      if (chapter) params.append("chapter", chapter);
      if (review) params.append("requiresReview", "true");
      if (search) params.append("searchQuery", search);
      params.append("sortBy", sort);

      const response = await fetch(`/api/anachronisms?${params.toString()}`);

      if (!response.ok) {
        throw new Error("Failed to fetch anachronisms");
      }

      const data: AnachronismResponse = await response.json();

      setResults(data.results);
      setTotal(data.total);
      setAllCategories(data.allCategories);
      setSeverityDistribution(data.severityDistribution);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (selectedSeverity) params.append("severity", selectedSeverity);
    if (selectedCategory) params.append("category", selectedCategory);
    if (selectedTitle) params.append("title", selectedTitle);
    if (selectedChapter) params.append("chapter", selectedChapter);
    if (requiresReview) params.append("requiresReview", "true");
    if (searchQuery) params.append("searchQuery", searchQuery);
    if (sortBy !== "severity") params.append("sortBy", sortBy);

    router.push(`/anachronisms?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedSeverity("");
    setSelectedCategory("");
    setSelectedTitle("");
    setSelectedChapter("");
    setRequiresReview(false);
    setSearchQuery("");
    setSortBy("severity");
    router.push("/anachronisms");
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return "text-red-600 bg-red-50 border-red-300";
      case "HIGH": return "text-orange-600 bg-orange-50 border-orange-300";
      case "MEDIUM": return "text-yellow-600 bg-yellow-50 border-yellow-300";
      case "LOW": return "text-slate-600 bg-slate-50 border-slate-300";
      default: return "text-slate-600 bg-slate-50 border-slate-300";
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return "bg-red-600";
      case "HIGH": return "bg-orange-600";
      case "MEDIUM": return "bg-yellow-600";
      case "LOW": return "bg-slate-600";
      default: return "bg-slate-600";
    }
  };

  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Anachronisms" }
      ]} />

      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Anachronistic Language Detection</h1>
            <p className="text-slate-600">
              Sections containing outdated, obsolete, or potentially problematic language that may require review.
            </p>
          </div>

          {/* Statistics Cards */}
          {severityDistribution.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {severityDistribution.map((item) => (
                <div
                  key={item.severity}
                  className={`rounded-lg border-2 p-4 ${getSeverityColor(item.severity)}`}
                >
                  <div className="text-2xl font-bold mb-1">{item.count}</div>
                  <div className="text-sm font-medium">{item.severity}</div>
                </div>
              ))}
            </div>
          )}

          {/* Filters */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Filters</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
              {/* Severity */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Severity
                </label>
                <select
                  value={selectedSeverity}
                  onChange={(e) => setSelectedSeverity(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="">All Severities</option>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Category
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="">All Categories</option>
                  {allCategories.map((cat) => (
                    <option key={cat.category} value={cat.category}>
                      {cat.category.replace(/_/g, ' ').toUpperCase()} ({cat.count})
                    </option>
                  ))}
                </select>
              </div>

              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Title
                </label>
                <select
                  value={selectedTitle}
                  onChange={(e) => setSelectedTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="">All Titles</option>
                  {availableTitles.map((title) => (
                    <option key={title} value={title}>{title}</option>
                  ))}
                </select>
              </div>

              {/* Chapter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Chapter
                </label>
                <select
                  value={selectedChapter}
                  onChange={(e) => setSelectedChapter(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                  disabled={!selectedTitle}
                >
                  <option value="">All Chapters</option>
                  {availableChapters.map((chapter) => (
                    <option key={chapter} value={chapter}>{chapter}</option>
                  ))}
                </select>
              </div>

              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Search
                </label>
                <input
                  type="text"
                  placeholder="Search summary or heading..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") applyFilters();
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="severity">Severity (Critical First)</option>
                  <option value="citation">Citation</option>
                  <option value="heading">Heading</option>
                </select>
              </div>
            </div>

            {/* Requires Review Checkbox */}
            <div className="mb-4">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresReview}
                  onChange={(e) => setRequiresReview(e.target.checked)}
                  className="w-4 h-4 text-red-600 border-slate-300 rounded focus:ring-red-500"
                />
                Show only sections requiring immediate review
              </label>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={applyFilters}
                className="px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-700 transition-colors font-medium"
              >
                Apply Filters
              </button>
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-slate-200 text-slate-700 rounded-md hover:bg-slate-300 transition-colors font-medium"
              >
                Clear All
              </button>
            </div>
          </div>

          {/* Active Filters */}
          {(appliedSeverity || appliedCategory || appliedTitle || appliedChapter || appliedRequiresReview || appliedSearchQuery) && (
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-teal-900">Active Filters:</span>
                {appliedSeverity && (
                  <span className="inline-block px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded">
                    Severity: {appliedSeverity}
                  </span>
                )}
                {appliedCategory && (
                  <span className="inline-block px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded">
                    Category: {appliedCategory.replace(/_/g, ' ')}
                  </span>
                )}
                {appliedTitle && (
                  <span className="inline-block px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded">
                    Title: {appliedTitle}
                  </span>
                )}
                {appliedChapter && (
                  <span className="inline-block px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded">
                    Chapter: {appliedChapter}
                  </span>
                )}
                {appliedRequiresReview && (
                  <span className="inline-block px-2 py-1 bg-red-100 text-red-800 text-xs rounded font-medium">
                    Requires Immediate Review
                  </span>
                )}
                {appliedSearchQuery && (
                  <span className="inline-block px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded">
                    Search: &ldquo;{appliedSearchQuery}&rdquo;
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Results Count */}
          <div className="mb-4">
            <p className="text-slate-600">
              Found <span className="font-semibold text-slate-900">{total}</span> section{total !== 1 ? 's' : ''} with anachronistic language
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-teal-600 border-r-transparent"></div>
              <p className="mt-4 text-slate-600">Loading anachronisms...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
              <p className="text-red-800 font-medium">Error: {error}</p>
            </div>
          )}

          {/* Results */}
          {!loading && !error && (
            <div className="space-y-4">
              {results.length === 0 ? (
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
                  <p className="text-slate-500">No anachronisms found matching the current filters.</p>
                </div>
              ) : (
                results.map((section) => (
                  <div
                    key={section.id}
                    className={`bg-white rounded-lg border-2 shadow-sm p-6 hover:shadow-md transition-shadow ${
                      section.requires_immediate_review ? 'border-red-400' : 'border-slate-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <Link
                          href={`/section/${section.id}`}
                          className="text-lg font-semibold text-teal-700 hover:text-teal-800 hover:underline"
                        >
                          {section.citation}
                        </Link>
                        <p className="text-slate-600 text-sm mt-1">{section.heading}</p>
                        <div className="text-xs text-slate-500 mt-1">
                          {section.title_label} › {section.chapter_label}
                        </div>
                      </div>
                      <div className="flex flex-col gap-2 items-end">
                        <span className={`inline-block px-3 py-1 text-white text-sm font-semibold rounded-full ${getSeverityBadgeColor(section.overall_severity)}`}>
                          {section.overall_severity}
                        </span>
                        {section.requires_immediate_review && (
                          <span className="inline-block px-2 py-1 bg-red-600 text-white text-xs font-medium rounded">
                            REVIEW REQUIRED
                          </span>
                        )}
                      </div>
                    </div>

                    {section.summary && (
                      <p className="text-slate-700 text-sm mb-4 leading-relaxed">
                        {section.summary}
                      </p>
                    )}

                    {section.indicators.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-xs font-semibold text-slate-600">
                          Indicators ({section.indicators.length}):
                        </span>
                        {section.indicators.slice(0, 3).map((indicator) => (
                          <div
                            key={indicator.id}
                            className="bg-slate-50 rounded p-3 border border-slate-200 text-sm"
                          >
                            <div className="flex gap-2 mb-1">
                              <span className={`inline-block px-2 py-0.5 text-white text-xs font-semibold rounded ${getSeverityBadgeColor(indicator.severity)}`}>
                                {indicator.severity}
                              </span>
                              <span className="inline-block px-2 py-0.5 bg-slate-200 text-slate-700 text-xs font-medium rounded">
                                {indicator.category.replace(/_/g, ' ').toUpperCase()}
                              </span>
                            </div>
                            <p className="text-slate-700 text-xs mt-1">{indicator.explanation}</p>
                          </div>
                        ))}
                        {section.indicators.length > 3 && (
                          <Link
                            href={`/section/${section.id}#anachronisms`}
                            className="text-xs text-teal-600 hover:text-teal-700 font-medium inline-block mt-1"
                          >
                            + {section.indicators.length - 3} more indicator{section.indicators.length - 3 !== 1 ? 's' : ''}
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default function AnachronismsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-teal-600 border-r-transparent"></div>
      </div>
    }>
      <AnachronismsPageContent />
    </Suspense>
  );
}
