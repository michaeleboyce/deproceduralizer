"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navigation from "@/components/Navigation";
import { Suspense } from "react";

interface ReportingSection {
  id: string;
  citation: string;
  heading: string;
  reporting_summary: string | null;
  title_label: string;
  chapter_label: string;
  tags: string[];
}

interface ReportingResponse {
  results: ReportingSection[];
  total: number;
  filters: {
    tag: string | null;
    title: string | null;
    chapter: string | null;
    searchQuery: string | null;
    sortBy: string;
  };
  allTags: string[];
}

function ReportingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [results, setResults] = useState<ReportingSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // Filter state (what user is currently selecting)
  const [selectedTag, setSelectedTag] = useState("");
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("citation");
  const [viewMode, setViewMode] = useState<"cards" | "grouped">("cards");

  // Applied filters (what's actually in the URL and active)
  const [appliedTag, setAppliedTag] = useState("");
  const [appliedTitle, setAppliedTitle] = useState("");
  const [appliedChapter, setAppliedChapter] = useState("");
  const [appliedSearchQuery, setAppliedSearchQuery] = useState("");

  // Available options
  const [allTags, setAllTags] = useState<string[]>([]);
  const [availableTitles, setAvailableTitles] = useState<string[]>([]);
  const [availableChapters, setAvailableChapters] = useState<string[]>([]);

  // Grouped view state
  const [expandedTags, setExpandedTags] = useState<Set<string>>(new Set());

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
    const urlTag = searchParams.get("tag") || "";
    const urlTitle = searchParams.get("title") || "";
    const urlChapter = searchParams.get("chapter") || "";
    const urlSearchQuery = searchParams.get("searchQuery") || "";
    const urlSortBy = searchParams.get("sortBy") || "citation";
    const urlViewMode = (searchParams.get("viewMode") || "cards") as "cards" | "grouped";

    // Set both selected (for form) and applied (for display)
    setSelectedTag(urlTag);
    setSelectedTitle(urlTitle);
    setSelectedChapter(urlChapter);
    setSearchQuery(urlSearchQuery);
    setSortBy(urlSortBy);
    setViewMode(urlViewMode);

    setAppliedTag(urlTag);
    setAppliedTitle(urlTitle);
    setAppliedChapter(urlChapter);
    setAppliedSearchQuery(urlSearchQuery);

    fetchReportingData(urlTag, urlTitle, urlChapter, urlSearchQuery, urlSortBy);
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

  const fetchReportingData = async (
    tag: string = selectedTag,
    title: string = selectedTitle,
    chapter: string = selectedChapter,
    search: string = searchQuery,
    sort: string = sortBy
  ) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (tag) params.append("tag", tag);
      if (title) params.append("title", title);
      if (chapter) params.append("chapter", chapter);
      if (search) params.append("searchQuery", search);
      params.append("sortBy", sort);

      const response = await fetch(`/api/reporting?${params.toString()}`);

      if (!response.ok) {
        throw new Error("Failed to fetch reporting requirements");
      }

      const data: ReportingResponse = await response.json();
      setResults(data.results);
      setTotal(data.total);
      setAllTags(data.allTags);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const updateFilters = () => {
    const params = new URLSearchParams();
    if (selectedTag) params.append("tag", selectedTag);
    if (selectedTitle) params.append("title", selectedTitle);
    if (selectedChapter) params.append("chapter", selectedChapter);
    if (searchQuery) params.append("searchQuery", searchQuery);
    if (sortBy !== "citation") params.append("sortBy", sortBy);
    if (viewMode !== "cards") params.append("viewMode", viewMode);

    router.push(`/reporting?${params.toString()}`);
  };

  const clearFilters = () => {
    setSelectedTag("");
    setSelectedTitle("");
    setSelectedChapter("");
    setSearchQuery("");
    setSortBy("citation");
    router.push("/reporting");
  };

  const hasActiveFilters = appliedTag || appliedTitle || appliedChapter || appliedSearchQuery;

  // Group results by tags for grouped view
  const groupedResults = () => {
    const groups: { [key: string]: ReportingSection[] } = {};

    results.forEach((section) => {
      if (section.tags && section.tags.length > 0) {
        section.tags.forEach((tag) => {
          if (!groups[tag]) {
            groups[tag] = [];
          }
          groups[tag].push(section);
        });
      } else {
        if (!groups["Untagged"]) {
          groups["Untagged"] = [];
        }
        groups["Untagged"].push(section);
      }
    });

    return groups;
  };

  // Expand/collapse all for grouped view
  const expandAll = () => {
    const allTagNames = Object.keys(groupedResults());
    setExpandedTags(new Set(allTagNames));
  };

  const collapseAll = () => {
    setExpandedTags(new Set());
  };

  const toggleTag = (tag: string) => {
    const newExpanded = new Set(expandedTags);
    if (newExpanded.has(tag)) {
      newExpanded.delete(tag);
    } else {
      newExpanded.add(tag);
    }
    setExpandedTags(newExpanded);
  };

  const renderCard = (section: ReportingSection) => (
    <div
      key={section.id}
      className="bg-white border border-slate-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
    >
      <Link
        href={`/section/${section.id}`}
        className="text-teal-700 font-semibold hover:text-teal-900 transition-colors text-lg"
      >
        {section.citation}
      </Link>
      <h3 className="text-slate-900 font-bold mt-2 mb-3">{section.heading}</h3>

      {/* Title/Chapter badges */}
      <div className="flex gap-2 mb-3">
        <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
          {section.title_label}
        </span>
        {section.chapter_label && (
          <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
            {section.chapter_label}
          </span>
        )}
      </div>

      {/* Reporting summary */}
      {section.reporting_summary && (
        <p className="text-slate-700 text-sm mb-3 leading-relaxed">
          {section.reporting_summary}
        </p>
      )}

      {/* Tags */}
      {section.tags && section.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {section.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded-full border border-purple-200"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <>
      <Navigation
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Reporting Requirements" },
        ]}
      />

      <div className="min-h-screen bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 mb-3">
              Reporting Requirements
            </h1>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-teal-700">
                {loading ? "..." : total}
              </span>
              <span className="text-slate-600">
                {total === 1 ? "requirement" : "requirements"} found
              </span>
            </div>
          </div>

          {/* Filters Panel */}
          <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
              {/* Search Input */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Search Summaries
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search in summaries..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 placeholder:text-slate-400"
                />
              </div>

              {/* Tag Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Filter by Tag
                </label>
                <select
                  value={selectedTag}
                  onChange={(e) => setSelectedTag(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
                >
                  <option value="">All Tags</option>
                  {allTags.map((tag) => (
                    <option key={tag} value={tag}>
                      {tag}
                    </option>
                  ))}
                </select>
              </div>

              {/* Title Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Filter by Title
                </label>
                <select
                  value={selectedTitle}
                  onChange={(e) => setSelectedTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
                >
                  <option value="">All Titles</option>
                  {availableTitles.map((title) => (
                    <option key={title} value={title}>
                      {title}
                    </option>
                  ))}
                </select>
              </div>

              {/* Chapter Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Filter by Chapter
                </label>
                <select
                  value={selectedChapter}
                  onChange={(e) => setSelectedChapter(e.target.value)}
                  disabled={!selectedTitle}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 disabled:bg-slate-50 disabled:text-slate-400"
                >
                  <option value="">All Chapters</option>
                  {availableChapters.map((chapter) => (
                    <option key={chapter} value={chapter}>
                      {chapter}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
                >
                  <option value="citation">Citation</option>
                  <option value="titleLabel">Title</option>
                  <option value="heading">Heading</option>
                </select>
              </div>

              {/* View Mode */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  View Mode
                </label>
                <select
                  value={viewMode}
                  onChange={(e) => setViewMode(e.target.value as "cards" | "grouped")}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900"
                >
                  <option value="cards">All Cards</option>
                  <option value="grouped">Grouped by Tags</option>
                </select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={updateFilters}
                className="bg-teal-700 text-white px-6 py-2 rounded-lg font-medium hover:bg-teal-800 transition-colors"
              >
                Apply Filters
              </button>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="bg-slate-200 text-slate-700 px-6 py-2 rounded-lg font-medium hover:bg-slate-300 transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>

            {/* Active Filters Display */}
            {hasActiveFilters && (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600 mb-2">Active Filters:</p>
                <div className="flex flex-wrap gap-2">
                  {appliedTag && (
                    <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm">
                      Tag: {appliedTag}
                    </span>
                  )}
                  {appliedTitle && (
                    <span className="bg-sky-100 text-sky-800 px-3 py-1 rounded-full text-sm">
                      Title: {appliedTitle}
                    </span>
                  )}
                  {appliedChapter && (
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                      Chapter: {appliedChapter}
                    </span>
                  )}
                  {appliedSearchQuery && (
                    <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-sm">
                      Search: "{appliedSearchQuery}"
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700"></div>
              <p className="mt-4 text-slate-600">Loading reporting requirements...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {/* Results */}
          {!loading && !error && (
            <>
              {viewMode === "cards" ? (
                // Card View
                results.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {results.map((section) => renderCard(section))}
                  </div>
                ) : (
                  <div className="text-center py-12 bg-white border border-slate-200 rounded-lg">
                    <p className="text-slate-600 text-lg">
                      No reporting requirements found
                    </p>
                    <p className="text-slate-500 text-sm mt-2">
                      Try adjusting your filters
                    </p>
                  </div>
                )
              ) : (
                // Grouped View
                <>
                  {/* Expand/Collapse All Buttons */}
                  <div className="flex gap-3 mb-4">
                    <button
                      onClick={expandAll}
                      className="bg-teal-700 text-white px-4 py-2 rounded-lg font-medium hover:bg-teal-800 transition-colors text-sm"
                    >
                      Expand All
                    </button>
                    <button
                      onClick={collapseAll}
                      className="bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium hover:bg-slate-300 transition-colors text-sm"
                    >
                      Collapse All
                    </button>
                  </div>

                  <div className="space-y-6">
                    {Object.entries(groupedResults())
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([tag, sections]) => (
                        <details
                          key={tag}
                          open={expandedTags.has(tag)}
                          className="bg-white border border-slate-200 rounded-lg"
                        >
                          <summary
                            className="cursor-pointer px-6 py-4 font-bold text-slate-900 hover:bg-slate-50 transition-colors"
                            onClick={(e) => {
                              e.preventDefault();
                              toggleTag(tag);
                            }}
                          >
                            <span className="text-purple-700">{tag}</span>
                            <span className="ml-2 text-slate-500 font-normal">
                              ({sections.length})
                            </span>
                          </summary>
                          <div className="px-6 pb-6 pt-2 space-y-4">
                            {sections.map((section) => renderCard(section))}
                          </div>
                        </details>
                      ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default function ReportingPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ReportingPageContent />
    </Suspense>
  );
}
