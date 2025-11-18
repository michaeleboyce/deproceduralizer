"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import DiffMatchPatch from "diff-match-patch";

interface SimilarSection {
  id: string;
  citation: string;
  heading: string;
  similarity: number;
  classification?: string | null;
  explanation?: string | null;
  modelUsed?: string | null;
}

interface SimilarSectionsListProps {
  currentSectionId: string;
  currentSectionCitation: string;
  similarSections: SimilarSection[];
}

interface SectionData {
  id: string;
  citation: string;
  heading: string;
  textPlain: string;
}

type ViewMode = "unified" | "split";

const getClassificationBadgeColor = (classification: string | null | undefined) => {
  if (!classification) return "bg-slate-500 text-white";

  const colors: Record<string, string> = {
    related: "bg-emerald-600 text-white",
    duplicate: "bg-amber-600 text-white",
    superseded: "bg-blue-600 text-white",
    conflicting: "bg-red-600 text-white",
    unrelated: "bg-slate-500 text-white",
    superseted: "bg-blue-600 text-white", // Handle typo
  };

  return colors[classification.toLowerCase()] || "bg-slate-500 text-white";
};

export default function SimilarSectionsList({
  currentSectionId,
  currentSectionCitation,
  similarSections,
}: SimilarSectionsListProps) {
  const [expandedSectionId, setExpandedSectionId] = useState<string | null>(
    null
  );
  const [viewMode, setViewMode] = useState<ViewMode>("unified");
  const [currentSection, setCurrentSection] = useState<SectionData | null>(
    null
  );
  const [comparisonSection, setComparisonSection] =
    useState<SectionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch sections when a comparison is expanded
  useEffect(() => {
    if (!expandedSectionId) {
      setCurrentSection(null);
      setComparisonSection(null);
      return;
    }

    const fetchSections = async () => {
      try {
        setLoading(true);
        setError(null);

        const [res1, res2] = await Promise.all([
          fetch(`/api/section/${currentSectionId}`),
          fetch(`/api/section/${expandedSectionId}`),
        ]);

        if (!res1.ok || !res2.ok) {
          throw new Error("Failed to fetch sections");
        }

        const data1 = await res1.json();
        const data2 = await res2.json();

        setCurrentSection(data1);
        setComparisonSection(data2);
      } catch (err) {
        setError("Failed to load sections for comparison");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSections();
  }, [expandedSectionId, currentSectionId]);

  const handleCompare = (
    sectionId: string,
    e: React.MouseEvent<HTMLButtonElement>
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setExpandedSectionId(sectionId);
  };

  const handleHideComparison = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setExpandedSectionId(null);
  };

  const renderUnifiedDiff = (text1: string, text2: string) => {
    const dmp = new DiffMatchPatch();
    const diffs = dmp.diff_main(text1, text2);
    dmp.diff_cleanupSemantic(diffs);

    return (
      <div className="p-4 font-mono text-sm whitespace-pre-wrap break-words">
        {diffs.map((diff, index) => {
          const [operation, text] = diff;
          if (operation === 0) {
            // No change
            return (
              <span key={index} className="text-slate-700">
                {text}
              </span>
            );
          } else if (operation === -1) {
            // Deleted
            return (
              <span
                key={index}
                className="bg-red-50 text-red-900 line-through"
              >
                {text}
              </span>
            );
          } else {
            // Added
            return (
              <span key={index} className="bg-green-50 text-green-900">
                {text}
              </span>
            );
          }
        })}
      </div>
    );
  };

  const renderSplitDiff = (text1: string, text2: string) => {
    return (
      <div className="grid grid-cols-2 gap-0 divide-x divide-slate-300">
        {/* Left side - Current Section */}
        <div className="p-4 bg-slate-50">
          <div className="font-mono text-sm whitespace-pre-wrap break-words text-slate-800">
            {text1}
          </div>
        </div>
        {/* Right side - Comparison Section */}
        <div className="p-4 bg-slate-100">
          <div className="font-mono text-sm whitespace-pre-wrap break-words text-slate-800">
            {text2}
          </div>
        </div>
      </div>
    );
  };

  if (similarSections.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
      <h2 className="text-xl font-semibold text-slate-900 mb-4">
        Similar Sections
      </h2>
      <p className="text-sm text-slate-600 mb-4">
        Sections with similar content based on semantic analysis
      </p>
      <div className="space-y-3">
        {similarSections.map((similar) => (
          <div key={similar.id}>
            <div className="block p-4 bg-sky-50 border border-sky-200 rounded-lg">
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={`/section/${similar.id}`}
                  className="flex-1 hover:opacity-80 transition-opacity"
                >
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-sm text-sky-700 font-medium">
                      {similar.citation}
                    </span>
                    <span className="inline-block px-2 py-0.5 bg-sky-600 text-white text-xs font-semibold rounded-full">
                      {(similar.similarity * 100).toFixed(1)}% match
                    </span>
                    {similar.classification && (
                      <span className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-full capitalize ${getClassificationBadgeColor(similar.classification)}`}>
                        {similar.classification}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-700 text-sm">{similar.heading}</p>
                  {similar.explanation && (
                    <p className="text-slate-600 text-xs mt-1 italic">
                      {similar.explanation}
                    </p>
                  )}
                  {similar.modelUsed && (
                    <p className="text-slate-400 text-xs mt-0.5">
                      Classified by: {similar.modelUsed}
                    </p>
                  )}
                </Link>
                {expandedSectionId === similar.id ? (
                  <button
                    onClick={handleHideComparison}
                    className="flex-shrink-0 px-3 py-1.5 bg-slate-500 text-white text-xs font-medium rounded hover:bg-slate-600 transition-colors"
                  >
                    Hide Comparison
                  </button>
                ) : (
                  <button
                    onClick={(e) => handleCompare(similar.id, e)}
                    className="flex-shrink-0 px-3 py-1.5 bg-sky-600 text-white text-xs font-medium rounded hover:bg-sky-700 transition-colors"
                  >
                    Compare
                  </button>
                )}
              </div>
            </div>

            {/* Inline Diff View */}
            {expandedSectionId === similar.id && (
              <div className="mt-3 p-4 bg-slate-50 border border-slate-300 rounded-lg">
                {/* View Mode Toggle */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-700">
                      View:
                    </span>
                    <div className="inline-flex rounded-lg border border-slate-300 bg-white shadow-sm">
                      <button
                        onClick={() => setViewMode("unified")}
                        className={`px-3 py-1.5 text-xs font-medium rounded-l-lg transition-colors ${
                          viewMode === "unified"
                            ? "bg-sky-600 text-white"
                            : "bg-white text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        Unified
                      </button>
                      <button
                        onClick={() => setViewMode("split")}
                        className={`px-3 py-1.5 text-xs font-medium rounded-r-lg transition-colors ${
                          viewMode === "split"
                            ? "bg-sky-600 text-white"
                            : "bg-white text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        Side-by-Side
                      </button>
                    </div>
                  </div>
                </div>

                {/* Loading State */}
                {loading && (
                  <div className="text-center py-8">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-sky-600"></div>
                    <p className="text-slate-600 text-sm mt-2">
                      Loading comparison...
                    </p>
                  </div>
                )}

                {/* Error State */}
                {error && (
                  <div className="text-center py-8">
                    <p className="text-red-600 text-sm">{error}</p>
                  </div>
                )}

                {/* Diff Viewer */}
                {!loading && !error && currentSection && comparisonSection && (
                  <div className="bg-white rounded-lg border border-slate-300 overflow-hidden shadow-sm">
                    {/* Header */}
                    <div className="p-3 bg-slate-100 border-b border-slate-300">
                      <div
                        className={
                          viewMode === "split"
                            ? "grid grid-cols-2 gap-4 text-sm divide-x divide-slate-300"
                            : "text-sm"
                        }
                      >
                        {viewMode === "split" ? (
                          <>
                            <div className="pr-4">
                              <span className="font-semibold text-slate-900">
                                {currentSection.citation}
                              </span>
                              <p className="text-slate-600 text-xs mt-0.5">
                                {currentSection.heading}
                              </p>
                            </div>
                            <div className="pl-4">
                              <span className="font-semibold text-slate-900">
                                {comparisonSection.citation}
                              </span>
                              <p className="text-slate-600 text-xs mt-0.5">
                                {comparisonSection.heading}
                              </p>
                            </div>
                          </>
                        ) : (
                          <div>
                            <div className="mb-2">
                              <span className="font-semibold text-slate-900">
                                {currentSection.citation}
                              </span>
                              <span className="mx-2 text-slate-500">vs</span>
                              <span className="font-semibold text-slate-900">
                                {comparisonSection.citation}
                              </span>
                            </div>
                            <div className="flex gap-2 text-xs">
                              <div className="flex items-center gap-1">
                                <span className="inline-block w-3 h-3 bg-red-50 border border-red-300 rounded"></span>
                                <span className="text-slate-600">Removed</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <span className="inline-block w-3 h-3 bg-green-50 border border-green-300 rounded"></span>
                                <span className="text-slate-600">Added</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Diff Content */}
                    <div className="max-h-[600px] overflow-auto">
                      {viewMode === "unified"
                        ? renderUnifiedDiff(
                            currentSection.textPlain,
                            comparisonSection.textPlain
                          )
                        : renderSplitDiff(
                            currentSection.textPlain,
                            comparisonSection.textPlain
                          )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
