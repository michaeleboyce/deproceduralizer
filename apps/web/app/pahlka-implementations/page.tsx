"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navigation from "@/components/Navigation";
import { Suspense } from "react";

interface ImplementationIndicator {
  id: number;
  category: string;
  complexity: string;
  implementationApproach: string;
  effortEstimate: string | null;
  explanation: string;
  matchedPhrases: string[];
}

interface ImplementationSection {
  id: string;
  citation: string;
  heading: string;
  title_label: string;
  chapter_label: string;
  has_implementation_issues: boolean;
  overall_complexity: string;
  summary: string | null;
  requires_technical_review: boolean;
  model_used: string | null;
  analyzed_at: string;
  indicators: ImplementationIndicator[];
}

interface ImplementationResponse {
  results: ImplementationSection[];
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
  technicalReviewStats: { requires_review: number; total: number };
}

function PahlkaImplementationsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [results, setResults] = useState<ImplementationSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // Filter state
  const [selectedComplexity, setSelectedComplexity] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [requiresTechnicalReview, setRequiresTechnicalReview] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("complexity");

  // Applied filters
  const [appliedComplexity, setAppliedComplexity] = useState("");
  const [appliedCategory, setAppliedCategory] = useState("");
  const [appliedTitle, setAppliedTitle] = useState("");
  const [appliedChapter, setAppliedChapter] = useState("");
  const [appliedRequiresTechnicalReview, setAppliedRequiresTechnicalReview] = useState(false);
  const [appliedSearchQuery, setAppliedSearchQuery] = useState("");

  // Available options
  const [allCategories, setAllCategories] = useState<Array<{ category: string; count: number }>>([]);
  const [complexityDistribution, setComplexityDistribution] = useState<Array<{ complexity: string; count: number }>>([]);
  const [technicalReviewStats, setTechnicalReviewStats] = useState<{ requires_review: number; total: number }>({ requires_review: 0, total: 0 });
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
    const urlComplexity = searchParams.get("complexity") || "";
    const urlCategory = searchParams.get("category") || "";
    const urlTitle = searchParams.get("title") || "";
    const urlChapter = searchParams.get("chapter") || "";
    const urlRequiresTechnicalReview = searchParams.get("requiresTechnicalReview") === "true";
    const urlSearchQuery = searchParams.get("searchQuery") || "";
    const urlSortBy = searchParams.get("sortBy") || "complexity";

    setSelectedComplexity(urlComplexity);
    setSelectedCategory(urlCategory);
    setSelectedTitle(urlTitle);
    setSelectedChapter(urlChapter);
    setRequiresTechnicalReview(urlRequiresTechnicalReview);
    setSearchQuery(urlSearchQuery);
    setSortBy(urlSortBy);

    setAppliedComplexity(urlComplexity);
    setAppliedCategory(urlCategory);
    setAppliedTitle(urlTitle);
    setAppliedChapter(urlChapter);
    setAppliedRequiresTechnicalReview(urlRequiresTechnicalReview);
    setAppliedSearchQuery(urlSearchQuery);

    fetchImplementationData(urlComplexity, urlCategory, urlTitle, urlChapter, urlRequiresTechnicalReview, urlSearchQuery, urlSortBy);
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

  const fetchImplementationData = async (
    complexity: string = selectedComplexity,
    category: string = selectedCategory,
    title: string = selectedTitle,
    chapter: string = selectedChapter,
    requiresReview: boolean = requiresTechnicalReview,
    search: string = searchQuery,
    sort: string = sortBy
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (complexity) params.append("complexity", complexity);
      if (category) params.append("category", category);
      if (title) params.append("title", title);
      if (chapter) params.append("chapter", chapter);
      if (requiresReview) params.append("requiresTechnicalReview", "true");
      if (search) params.append("searchQuery", search);
      params.append("sortBy", sort);

      const url = `/api/pahlka-implementations?${params.toString()}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ImplementationResponse = await response.json();
      setResults(data.results);
      setTotal(data.total);
      setAllCategories(data.allCategories);
      setComplexityDistribution(data.complexityDistribution);
      setTechnicalReviewStats(data.technicalReviewStats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      console.error("Error fetching implementation data:", err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (selectedComplexity) params.append("complexity", selectedComplexity);
    if (selectedCategory) params.append("category", selectedCategory);
    if (selectedTitle) params.append("title", selectedTitle);
    if (selectedChapter) params.append("chapter", selectedChapter);
    if (requiresTechnicalReview) params.append("requiresTechnicalReview", "true");
    if (searchQuery) params.append("searchQuery", searchQuery);
    params.append("sortBy", sortBy);

    router.push(`/pahlka-implementations?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedComplexity("");
    setSelectedCategory("");
    setSelectedTitle("");
    setSelectedChapter("");
    setRequiresTechnicalReview(false);
    setSearchQuery("");
    setSortBy("complexity");
    router.push("/pahlka-implementations");
  };

  const getComplexityColor = (complexity: string): string => {
    switch (complexity) {
      case "HIGH":
        return "text-red-600 dark:text-red-400";
      case "MEDIUM":
        return "text-yellow-600 dark:text-yellow-400";
      case "LOW":
        return "text-blue-600 dark:text-blue-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  };

  const getComplexityBgColor = (complexity: string): string => {
    switch (complexity) {
      case "HIGH":
        return "bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200";
      case "MEDIUM":
        return "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200";
      case "LOW":
        return "bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200";
      default:
        return "bg-gray-100 dark:bg-gray-900/20 text-gray-800 dark:text-gray-200";
    }
  };

  const formatCategoryName = (category: string): string => {
    return category
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const hasActiveFilters =
    appliedComplexity ||
    appliedCategory ||
    appliedTitle ||
    appliedChapter ||
    appliedRequiresTechnicalReview ||
    appliedSearchQuery;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Pahlka Implementation Analysis
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Sections analyzed for implementation complexity using Jennifer Pahlka's "Recoding America" framework
          </p>
        </div>

        {/* Stats Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Total sections */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              Total Sections
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white">
              {total.toLocaleString()}
            </div>
          </div>

          {/* Complexity distribution */}
          {complexityDistribution.map((dist) => (
            <div key={dist.complexity} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                {dist.complexity} Complexity
              </div>
              <div className={`text-3xl font-bold ${getComplexityColor(dist.complexity)}`}>
                {dist.count.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                {total > 0 ? `${Math.round((dist.count / total) * 100)}%` : "0%"}
              </div>
            </div>
          ))}

          {/* Technical review */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              Needs Technical Review
            </div>
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {technicalReviewStats.requires_review.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              {technicalReviewStats.total > 0
                ? `${Math.round((technicalReviewStats.requires_review / technicalReviewStats.total) * 100)}%`
                : "0%"}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Filters</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {/* Complexity filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Complexity
              </label>
              <select
                value={selectedComplexity}
                onChange={(e) => setSelectedComplexity(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">All Complexities</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            {/* Category filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">All Categories</option>
                {allCategories.map((cat) => (
                  <option key={cat.category} value={cat.category}>
                    {formatCategoryName(cat.category)} ({cat.count})
                  </option>
                ))}
              </select>
            </div>

            {/* Title filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Title
              </label>
              <select
                value={selectedTitle}
                onChange={(e) => setSelectedTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">All Titles</option>
                {availableTitles.map((title) => (
                  <option key={title} value={title}>
                    {title}
                  </option>
                ))}
              </select>
            </div>

            {/* Chapter filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Chapter
              </label>
              <select
                value={selectedChapter}
                onChange={(e) => setSelectedChapter(e.target.value)}
                disabled={!selectedTitle}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">All Chapters</option>
                {availableChapters.map((chapter) => (
                  <option key={chapter} value={chapter}>
                    {chapter}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort by */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="complexity">Complexity</option>
                <option value="citation">Citation</option>
                <option value="heading">Heading</option>
              </select>
            </div>
          </div>

          {/* Search and checkboxes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Search
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search in summary or heading..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div className="flex items-end">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresTechnicalReview}
                  onChange={(e) => setRequiresTechnicalReview(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Requires Technical Review
                </span>
              </label>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={applyFilters}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Apply Filters
            </button>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Results ({total.toLocaleString()} sections)
            </h2>
          </div>

          {loading && (
            <div className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
              Loading implementation analysis...
            </div>
          )}

          {error && (
            <div className="px-6 py-12 text-center text-red-600 dark:text-red-400">
              Error: {error}
            </div>
          )}

          {!loading && !error && results.length === 0 && (
            <div className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
              No implementation issues found matching your filters.
            </div>
          )}

          {!loading && !error && results.length > 0 && (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {results.map((section) => (
                <div key={section.id} className="px-6 py-6 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  {/* Section header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <Link
                        href={`/sections/${section.id}`}
                        className="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        {section.citation}
                      </Link>
                      <p className="text-gray-700 dark:text-gray-300 mt-1">{section.heading}</p>
                      <div className="flex gap-2 mt-2 text-sm text-gray-500 dark:text-gray-400">
                        <span>{section.title_label}</span>
                        {section.chapter_label && (
                          <>
                            <span>•</span>
                            <span>{section.chapter_label}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2 ml-4">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getComplexityBgColor(
                          section.overall_complexity
                        )}`}
                      >
                        {section.overall_complexity}
                      </span>
                      {section.requires_technical_review && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-200">
                          Tech Review
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Summary */}
                  {section.summary && (
                    <div className="mb-4 text-gray-700 dark:text-gray-300 text-sm bg-gray-50 dark:bg-gray-700/50 p-3 rounded">
                      {section.summary}
                    </div>
                  )}

                  {/* Indicators */}
                  {section.indicators && section.indicators.length > 0 && (
                    <div className="space-y-3">
                      {section.indicators.map((indicator) => (
                        <div
                          key={indicator.id}
                          className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 bg-white dark:bg-gray-800"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <span className="text-sm font-medium text-gray-900 dark:text-white">
                                {formatCategoryName(indicator.category)}
                              </span>
                            </div>
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getComplexityBgColor(
                                indicator.complexity
                              )}`}
                            >
                              {indicator.complexity}
                            </span>
                          </div>

                          <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                            {indicator.explanation}
                          </p>

                          {indicator.implementationApproach && (
                            <div className="mb-3">
                              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                Implementation Approach:
                              </div>
                              <div className="text-sm text-gray-700 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                                {indicator.implementationApproach}
                              </div>
                            </div>
                          )}

                          {indicator.effortEstimate && (
                            <div className="mb-3">
                              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                Effort Estimate:
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {indicator.effortEstimate}
                              </div>
                            </div>
                          )}

                          {indicator.matchedPhrases && indicator.matchedPhrases.length > 0 && (
                            <div>
                              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                Matched Phrases:
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {indicator.matchedPhrases.map((phrase, idx) => (
                                  <span
                                    key={idx}
                                    className="inline-flex items-center px-2 py-1 rounded text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200"
                                  >
                                    "{phrase}"
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PahlkaImplementationsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="text-gray-500 dark:text-gray-400">Loading...</div>
        </div>
      }
    >
      <PahlkaImplementationsPageContent />
    </Suspense>
  );
}
