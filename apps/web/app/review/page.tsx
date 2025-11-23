"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navigation from "@/components/Navigation";
import AnachronismIndicatorCard from "@/components/AnachronismIndicatorCard";
import ImplementationIndicatorCard from "@/components/ImplementationIndicatorCard";
import { Download, BarChart3, List, CheckCircle2, ExternalLink } from "lucide-react";
import { Suspense } from "react";

interface QueueItem {
  id: string | number;
  itemType: string;
  category?: string;
  severity?: string;
  complexity?: string;
  explanation: string;
  sectionId: string;
  citation: string;
  heading: string;
  titleLabel: string;
  chapterLabel: string;
}

interface ReviewedFeedback {
  id: string;
  itemType: string;
  itemId: string;
  reviewerId: string;
  reviewerName: string;
  rating: string;
  comment: string;
  suggestedCategory?: string;
  suggestedSeverity?: string;
  suggestedComplexity?: string;
  reviewedAt: string;
  sectionId?: string;
}

interface Stats {
  ratingDistribution: Array<{ rating: string; count: string; reviewer_count: string }>;
  itemTypeDistribution: Array<{ item_type: string; count: string }>;
  reviewerStatistics: Array<{
    reviewer_id: string;
    reviewer_name: string;
    review_count: string;
  }>;
  totals: {
    total_reviews: string;
    total_reviewers: string;
    total_items_reviewed: string;
    first_review_date: string;
    last_review_date: string;
  };
  falsePositiveRate: {
    false_positives: string;
    total: string;
    false_positive_percentage: string;
  };
}

function ReviewDashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<"queue" | "reviewed" | "analytics">("queue");
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [reviewedFeedback, setReviewedFeedback] = useState<ReviewedFeedback[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);

  // Filters
  const [itemTypeFilter, setItemTypeFilter] = useState("all");
  const [ratingFilter, setRatingFilter] = useState("");
  const [reviewerFilter, setReviewerFilter] = useState("");
  const [sortBy, setSortBy] = useState("severity");

  useEffect(() => {
    const tab = (searchParams.get("tab") as "queue" | "reviewed" | "analytics") || "queue";
    setActiveTab(tab);
  }, [searchParams]);

  useEffect(() => {
    if (activeTab === "queue") {
      loadQueue();
    } else if (activeTab === "reviewed") {
      loadReviewed();
    } else if (activeTab === "analytics") {
      loadStats();
    }
  }, [activeTab, itemTypeFilter, ratingFilter, reviewerFilter, sortBy]);

  async function loadQueue() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (itemTypeFilter !== "all") {
        params.append("itemType", itemTypeFilter);
      }
      params.append("sortBy", sortBy);
      params.append("limit", "50");

      const response = await fetch(`/api/feedback/queue?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to load queue");

      const data = await response.json();
      setQueueItems(data.items);
    } catch (error) {
      console.error("Error loading queue:", error);
    } finally {
      setLoading(false);
    }
  }

  async function loadReviewed() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (itemTypeFilter !== "all") {
        params.append("itemType", itemTypeFilter);
      }
      if (ratingFilter) {
        params.append("rating", ratingFilter);
      }
      if (reviewerFilter) {
        params.append("reviewerId", reviewerFilter);
      }
      params.append("includeContext", "true");

      const response = await fetch(`/api/feedback?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to load reviewed items");

      const data = await response.json();
      setReviewedFeedback(data.feedback);
    } catch (error) {
      console.error("Error loading reviewed items:", error);
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    setLoading(true);
    try {
      const response = await fetch("/api/feedback/stats");
      if (!response.ok) throw new Error("Failed to load stats");

      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Error loading stats:", error);
    } finally {
      setLoading(false);
    }
  }

  async function exportFeedback(format: "json" | "csv") {
    const params = new URLSearchParams();
    params.append("format", format);
    if (itemTypeFilter !== "all") {
      params.append("itemType", itemTypeFilter);
    }
    if (ratingFilter) {
      params.append("rating", ratingFilter);
    }
    if (reviewerFilter) {
      params.append("reviewerId", reviewerFilter);
    }

    window.open(`/api/feedback/export?${params.toString()}`, "_blank");
  }

  function changeTab(tab: "queue" | "reviewed" | "analytics") {
    router.push(`/review?tab=${tab}`);
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Review Dashboard</h1>
          <p className="text-slate-600">
            Review AI findings, provide feedback, and track model accuracy
          </p>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex space-x-1 bg-slate-200 p-1 rounded-lg">
            <button
              onClick={() => changeTab("queue")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                activeTab === "queue"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <List size={16} />
              Queue
            </button>
            <button
              onClick={() => changeTab("reviewed")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                activeTab === "reviewed"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <CheckCircle2 size={16} />
              Reviewed
            </button>
            <button
              onClick={() => changeTab("analytics")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
                activeTab === "analytics"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <BarChart3 size={16} />
              Analytics
            </button>
          </div>

          {/* Export Button (shown on reviewed tab) */}
          {activeTab === "reviewed" && (
            <div className="flex gap-2">
              <button
                onClick={() => exportFeedback("csv")}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 flex items-center gap-2"
              >
                <Download size={16} />
                Export CSV
              </button>
              <button
                onClick={() => exportFeedback("json")}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 flex items-center gap-2"
              >
                <Download size={16} />
                Export JSON
              </button>
            </div>
          )}
        </div>

        {/* Filters */}
        {(activeTab === "queue" || activeTab === "reviewed") && (
          <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Item Type
                </label>
                <select
                  value={itemTypeFilter}
                  onChange={(e) => setItemTypeFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 bg-white"
                >
                  <option value="all">All Types</option>
                  <option value="anachronism_indicator">Anachronisms</option>
                  <option value="implementation_indicator">Implementations</option>
                  <option value="similarity_classification">Conflicts</option>
                </select>
              </div>

              {activeTab === "queue" && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Sort By
                  </label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 bg-white"
                  >
                    <option value="severity">Severity (High to Low)</option>
                    <option value="complexity">Complexity (High to Low)</option>
                    <option value="citation">Citation (A to Z)</option>
                  </select>
                </div>
              )}

              {activeTab === "reviewed" && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Rating
                    </label>
                    <select
                      value={ratingFilter}
                      onChange={(e) => setRatingFilter(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 bg-white"
                    >
                      <option value="">All Ratings</option>
                      <option value="correct">Correct</option>
                      <option value="false_positive">False Positive</option>
                      <option value="wrong_category">Wrong Category</option>
                      <option value="wrong_severity">Wrong Severity</option>
                      <option value="missing_context">Missing Context</option>
                      <option value="needs_refinement">Needs Refinement</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Reviewer
                    </label>
                    <input
                      type="text"
                      value={reviewerFilter}
                      onChange={(e) => setReviewerFilter(e.target.value)}
                      placeholder="Filter by reviewer ID"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 placeholder:text-slate-400"
                    />
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-slate-500">Loading...</div>
          </div>
        ) : (
          <>
            {activeTab === "queue" && (
              <div className="space-y-4">
                {queueItems.length === 0 ? (
                  <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
                    <div className="text-4xl mb-4">🎉</div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">
                      Queue is Empty
                    </h3>
                    <p className="text-slate-600">
                      All items have been reviewed. Great work!
                    </p>
                  </div>
                ) : (
                  queueItems.map((item: any) => {
                    if (item.itemType === "anachronism_indicator") {
                      return (
                        <AnachronismIndicatorCard
                          key={item.id}
                          id={item.id}
                          category={item.category}
                          severity={item.severity}
                          modernEquivalent={item.modernEquivalent}
                          recommendation={item.recommendation}
                          explanation={item.explanation}
                          matchedPhrases={[]}
                          sectionId={item.sectionId}
                          citation={item.citation}
                          heading={item.heading}
                          titleLabel={item.titleLabel}
                          chapterLabel={item.chapterLabel}
                          overallSeverity={null}
                          requiresImmediateReview={false}
                          summary={null}
                        />
                      );
                    } else if (item.itemType === "implementation_indicator") {
                      return (
                        <ImplementationIndicatorCard
                          key={item.id}
                          id={item.id}
                          category={item.category}
                          complexity={item.complexity}
                          implementationApproach={item.implementationApproach}
                          effortEstimate={item.effortEstimate}
                          explanation={item.explanation}
                          matchedPhrases={[]}
                          sectionId={item.sectionId}
                          citation={item.citation}
                          heading={item.heading}
                          titleLabel={item.titleLabel}
                          chapterLabel={item.chapterLabel}
                          overallComplexity={null}
                          requiresTechnicalReview={false}
                          summary={null}
                        />
                      );
                    }
                    return null;
                  })
                )}
              </div>
            )}

            {activeTab === "reviewed" && (
              <div className="space-y-4">
                {reviewedFeedback.length === 0 ? (
                  <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
                    <p className="text-slate-600">
                      No reviewed items match your filters.
                    </p>
                  </div>
                ) : (
                  reviewedFeedback.map((feedback) => (
                    <div
                      key={feedback.id}
                      className="bg-white rounded-lg border border-slate-200 p-6"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex gap-2 flex-wrap">
                          <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded">
                            {feedback.itemType?.replace(/_/g, " ") || "Unknown"}
                          </span>
                          <span
                            className={`px-3 py-1 text-xs font-medium rounded ${
                              feedback.rating === "correct"
                                ? "bg-green-100 text-green-700"
                                : feedback.rating === "false_positive"
                                ? "bg-red-100 text-red-700"
                                : "bg-yellow-100 text-yellow-700"
                            }`}
                          >
                            {feedback.rating?.replace(/_/g, " ") || "Unknown"}
                          </span>
                        </div>
                        <div className="text-sm text-slate-500">
                          by {feedback.reviewerName || feedback.reviewerId || "Unknown"}
                        </div>
                      </div>

                      <div className="mb-3">
                        <span className="text-xs font-semibold text-slate-600 block mb-1">
                          Comment:
                        </span>
                        <p className="text-sm text-slate-700">{feedback.comment}</p>
                      </div>

                      {feedback.suggestedCategory && (
                        <div className="mb-3">
                          <span className="text-xs font-semibold text-slate-600">
                            Suggested Category:
                          </span>{" "}
                          <span className="text-sm text-slate-700">
                            {feedback.suggestedCategory}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-3">
                        <div className="text-xs text-slate-400">
                          Reviewed {new Date(feedback.reviewedAt).toLocaleString()}
                        </div>
                        {feedback.sectionId && (
                          <Link
                            href={`/section/${feedback.sectionId}`}
                            className="text-xs font-medium text-teal-700 hover:text-teal-800 flex items-center gap-1"
                          >
                            View Original
                            <ExternalLink size={12} />
                          </Link>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "analytics" && stats && (
              <div className="space-y-6">
                {/* Totals */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg border border-slate-200 p-6">
                    <div className="text-sm font-medium text-slate-600 mb-1">
                      Total Reviews
                    </div>
                    <div className="text-3xl font-bold text-slate-900">
                      {stats.totals.total_reviews}
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-6">
                    <div className="text-sm font-medium text-slate-600 mb-1">
                      Total Reviewers
                    </div>
                    <div className="text-3xl font-bold text-slate-900">
                      {stats.totals.total_reviewers}
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-6">
                    <div className="text-sm font-medium text-slate-600 mb-1">
                      Items Reviewed
                    </div>
                    <div className="text-3xl font-bold text-slate-900">
                      {stats.totals.total_items_reviewed}
                    </div>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-6">
                    <div className="text-sm font-medium text-slate-600 mb-1">
                      False Positive Rate
                    </div>
                    <div className="text-3xl font-bold text-red-600">
                      {stats.falsePositiveRate.false_positive_percentage}%
                    </div>
                  </div>
                </div>

                {/* Rating Distribution */}
                <div className="bg-white rounded-lg border border-slate-200 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">
                    Rating Distribution
                  </h3>
                  <div className="space-y-2">
                    {stats.ratingDistribution.map((item) => (
                      <div key={item.rating} className="flex items-center gap-4">
                        <div className="w-32 text-sm font-medium text-slate-700">
                          {item.rating.replace("_", " ")}
                        </div>
                        <div className="flex-1 bg-slate-100 rounded-full h-8 relative">
                          <div
                            className="bg-teal-600 h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium"
                            style={{
                              width: `${
                                (parseInt(item.count) /
                                  parseInt(stats.totals.total_reviews)) *
                                100
                              }%`,
                            }}
                          >
                            {item.count}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Reviewer Statistics */}
                <div className="bg-white rounded-lg border border-slate-200 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">
                    Reviewer Statistics
                  </h3>
                  <div className="space-y-3">
                    {stats.reviewerStatistics.map((reviewer) => (
                      <div
                        key={reviewer.reviewer_id}
                        className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0"
                      >
                        <div>
                          <div className="font-medium text-slate-900">
                            {reviewer.reviewer_name || reviewer.reviewer_id}
                          </div>
                          <div className="text-sm text-slate-500">
                            {reviewer.reviewer_id}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-teal-700">
                            {reviewer.review_count}
                          </div>
                          <div className="text-xs text-slate-500">reviews</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function ReviewDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <div className="text-slate-500">Loading...</div>
        </div>
      }
    >
      <ReviewDashboardContent />
    </Suspense>
  );
}
