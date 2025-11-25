"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Navigation from "@/components/Navigation";
import ImplementationIndicatorCard from "@/components/ImplementationIndicatorCard";
import { Suspense } from "react";
import { useFilters, useApiData } from "@/hooks";

interface ImplementationIndicator {
  id: number;
  category: string;
  complexity: string;
  implementationApproach: string;
  effortEstimate: string | null;
  explanation: string;
  matchedPhrases: string[];
  sectionId: string;
  citation: string;
  heading: string;
  titleLabel: string;
  chapterLabel: string;
  overallComplexity: string | null;
  requiresTechnicalReview: boolean;
  summary: string | null;
  modelUsed: string | null;
}

interface ImplementationResponse {
  results: ImplementationIndicator[];
  total: number;
  filters: {
    complexity: string | null;
    category: string | null;
    title: string | null;
    chapter: string | null;
    requiresTechnicalReview: boolean | null;
    searchQuery: string | null;
    sortBy: string;
  };
  allCategories: Array<{ category: string; count: number }>;
  complexityDistribution: Array<{ complexity: string; count: number }>;
}

function PahlkaImplementationsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Use shared hooks
  const filters = useFilters();
  const api = useApiData<ImplementationResponse>();

  // Implementation-specific filter state
  const [selectedComplexity, setSelectedComplexity] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [requiresTechnicalReview, setRequiresTechnicalReview] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("complexity");

  // Track applied filters for "Clear Filters" button
  const [appliedFilters, setAppliedFilters] = useState({
    complexity: "",
    category: "",
    title: "",
    chapter: "",
    requiresTechnicalReview: false,
    searchQuery: "",
    sortBy: "complexity",
  });

  // Auto-load from URL params on mount
  useEffect(() => {
    const urlComplexity = searchParams.get("complexity") || "";
    const urlCategory = searchParams.get("category") || "";
    const urlTitle = searchParams.get("title") || "";
    const urlChapter = searchParams.get("chapter") || "";
    const urlRequiresTechnicalReview = searchParams.get("requiresTechnicalReview") === "true";
    const urlSearchQuery = searchParams.get("searchQuery") || "";
    const urlSortBy = searchParams.get("sortBy") || "complexity";

    // Set form state
    setSelectedComplexity(urlComplexity);
    setSelectedCategory(urlCategory);
    filters.setSelectedTitle(urlTitle);
    filters.setSelectedChapter(urlChapter);
    setRequiresTechnicalReview(urlRequiresTechnicalReview);
    setSearchQuery(urlSearchQuery);
    setSortBy(urlSortBy);

    // Track applied filters
    setAppliedFilters({
      complexity: urlComplexity,
      category: urlCategory,
      title: urlTitle,
      chapter: urlChapter,
      requiresTechnicalReview: urlRequiresTechnicalReview,
      searchQuery: urlSearchQuery,
      sortBy: urlSortBy,
    });

    // Fetch data
    fetchData(urlComplexity, urlCategory, urlTitle, urlChapter, urlRequiresTechnicalReview, urlSearchQuery, urlSortBy);
  }, [searchParams]);

  const fetchData = useCallback(async (
    complexity: string,
    category: string,
    title: string,
    chapter: string,
    requiresReview: boolean,
    search: string,
    sort: string
  ) => {
    const params = new URLSearchParams();
    if (complexity) params.append("complexity", complexity);
    if (category) params.append("category", category);
    if (title) params.append("title", title);
    if (chapter) params.append("chapter", chapter);
    if (requiresReview) params.append("requiresTechnicalReview", "true");
    if (search) params.append("searchQuery", search);
    params.append("sortBy", sort);

    await api.fetchData("/api/pahlka-implementation-indicators", params);
  }, [api]);

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (selectedComplexity) params.append("complexity", selectedComplexity);
    if (selectedCategory) params.append("category", selectedCategory);
    if (filters.selectedTitle) params.append("title", filters.selectedTitle);
    if (filters.selectedChapter) params.append("chapter", filters.selectedChapter);
    if (requiresTechnicalReview) params.append("requiresTechnicalReview", "true");
    if (searchQuery) params.append("searchQuery", searchQuery);
    params.append("sortBy", sortBy);

    router.push(`/pahlka-implementations?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedComplexity("");
    setSelectedCategory("");
    filters.clearFilters();
    setRequiresTechnicalReview(false);
    setSearchQuery("");
    setSortBy("complexity");
    router.push("/pahlka-implementations");
  };

  // Derived state
  const results = api.data?.results || [];
  const total = api.data?.total || 0;
  const allCategories = api.data?.allCategories || [];
  const complexityDistribution = api.data?.complexityDistribution || [];

  const hasActiveFilters =
    appliedFilters.complexity ||
    appliedFilters.category ||
    appliedFilters.title ||
    appliedFilters.chapter ||
    appliedFilters.requiresTechnicalReview ||
    appliedFilters.searchQuery;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Pahlka Implementation Analysis
          </h1>
          <p className="text-gray-600">
            Individual implementation issues analyzed using Jennifer Pahlka's "Recoding America" framework
          </p>
        </div>

        {/* Stats Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600 mb-1">Total Issues</div>
            <div className="text-3xl font-bold text-gray-900">{total.toLocaleString()}</div>
          </div>
          {complexityDistribution.map((dist) => (
            <div key={dist.complexity} className="bg-white rounded-lg shadow p-6">
              <div className="text-sm font-medium text-gray-600 mb-1">{dist.complexity} Complexity</div>
              <div className={`text-3xl font-bold ${getComplexityColor(dist.complexity)}`}>
                {dist.count.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {total > 0 ? `${Math.round((dist.count / total) * 100)}%` : "0%"}
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {/* Complexity filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Complexity</label>
              <select
                value={selectedComplexity}
                onChange={(e) => setSelectedComplexity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
              >
                <option value="">All Complexities</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            {/* Category filter */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
              >
                <option value="">All Categories</option>
                {allCategories.map((cat) => (
                  <option key={cat.category} value={cat.category}>
                    {formatCategoryName(cat.category)} ({cat.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Title filter - using shared hook */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Title</label>
              <select
                value={filters.selectedTitle}
                onChange={(e) => filters.setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
              >
                <option value="">All Titles</option>
                {filters.availableTitles.map((title) => (
                  <option key={title} value={title}>{title}</option>
                ))}
              </select>
            </div>

            {/* Chapter filter - using shared hook */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Chapter</label>
              <select
                value={filters.selectedChapter}
                onChange={(e) => filters.setChapter(e.target.value)}
                disabled={!filters.selectedTitle}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="">All Chapters</option>
                {filters.availableChapters.map((chapter) => (
                  <option key={chapter} value={chapter}>{chapter}</option>
                ))}
              </select>
            </div>

            {/* Sort by */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
              >
                <option value="complexity">Complexity (High → Low)</option>
                <option value="category">Category (A → Z)</option>
                <option value="citation">Citation (A → Z)</option>
              </select>
            </div>
          </div>

          {/* Search and checkboxes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Search</label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search in explanation, approach, or section heading..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 placeholder:text-slate-400"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresTechnicalReview}
                  onChange={(e) => setRequiresTechnicalReview(e.target.checked)}
                  className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                />
                <span className="text-sm text-slate-700">Requires Technical Review</span>
              </label>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={applyFilters}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
            >
              Apply Filters
            </button>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Results ({total.toLocaleString()} implementation issues)
            </h2>
          </div>

          {api.loading && (
            <div className="px-6 py-12 text-center text-gray-500">
              Loading implementation analysis...
            </div>
          )}

          {api.error && (
            <div className="px-6 py-12 text-center text-red-600">
              Error: {api.error}
            </div>
          )}

          {!api.loading && !api.error && results.length === 0 && (
            <div className="px-6 py-12 text-center text-gray-500">
              No implementation issues found matching your filters.
            </div>
          )}

          {!api.loading && !api.error && results.length > 0 && (
            <div className="p-6 space-y-4">
              {results.map((indicator) => (
                <ImplementationIndicatorCard key={indicator.id} {...indicator} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper functions
function getComplexityColor(complexity: string): string {
  switch (complexity) {
    case "HIGH": return "text-red-600";
    case "MEDIUM": return "text-yellow-600";
    case "LOW": return "text-blue-600";
    default: return "text-gray-600";
  }
}

function formatCategoryName(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function PahlkaImplementationsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-gray-500">Loading...</div>
        </div>
      }
    >
      <PahlkaImplementationsPageContent />
    </Suspense>
  );
}
