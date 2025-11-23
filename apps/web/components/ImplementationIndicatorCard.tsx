'use client';

import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import BookmarkButton from './BookmarkButton';
import FeedbackButton from './FeedbackButton';
import MatchedPhraseChips from './MatchedPhraseChips';

interface ImplementationIndicatorCardProps {
  id: number;
  category: string;
  complexity: string;
  implementationApproach: string;
  effortEstimate: string | null;
  explanation: string;
  matchedPhrases: string[];
  // Section context
  sectionId: string;
  citation: string;
  heading: string;
  titleLabel: string;
  chapterLabel: string;
  // Parent analysis
  overallComplexity: string | null;
  requiresTechnicalReview: boolean;
  summary: string | null;
}

export default function ImplementationIndicatorCard({
  id,
  category,
  complexity,
  implementationApproach,
  effortEstimate,
  explanation,
  matchedPhrases,
  sectionId,
  citation,
  heading,
  titleLabel,
  chapterLabel,
  overallComplexity,
  requiresTechnicalReview,
}: ImplementationIndicatorCardProps) {
  function getComplexityColor(level: string) {
    switch (level) {
      case 'HIGH':
        return {
          bg: 'bg-purple-50',
          border: 'border-purple-200',
          badge: 'bg-purple-600',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          badge: 'bg-blue-600',
        };
      case 'LOW':
        return {
          bg: 'bg-indigo-50',
          border: 'border-indigo-200',
          badge: 'bg-indigo-600',
        };
      default:
        return {
          bg: 'bg-slate-50',
          border: 'border-slate-200',
          badge: 'bg-slate-600',
        };
    }
  }

  function formatCategory(cat: string): string {
    return cat
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  const colors = getComplexityColor(complexity);

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-6 hover:shadow-md transition-shadow`}>
      {/* Header with badges and action buttons */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex flex-wrap gap-2">
          <span className={`inline-block px-3 py-1 ${colors.badge} text-white text-xs font-bold rounded`}>
            {complexity}
          </span>
          <span className="inline-block px-2 py-1 bg-slate-200 text-slate-700 text-xs font-medium rounded">
            {formatCategory(category)}
          </span>
          {effortEstimate && (
            <span className="inline-block px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded">
              Effort: {effortEstimate}
            </span>
          )}
          {requiresTechnicalReview && (
            <span className="inline-block px-2 py-1 bg-orange-100 text-orange-700 text-xs font-bold rounded">
              Tech Review Required
            </span>
          )}
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <FeedbackButton
            itemType="implementation_indicator"
            itemId={id.toString()}
          />
          <BookmarkButton
            itemType="implementation_indicator"
            itemId={`${sectionId}:${id}`}
          />
        </div>
      </div>

      {/* Section context */}
      <div className="mb-4 pb-3 border-b border-slate-200">
        <Link
          href={`/section/${sectionId}#indicator-${id}`}
          className="text-sm font-semibold text-teal-700 hover:text-teal-900 hover:underline"
        >
          {citation}
        </Link>
        <p className="text-sm text-slate-700 mt-1">{heading}</p>
        <div className="flex gap-2 mt-1 text-xs text-slate-500">
          <span>{titleLabel}</span>
          {chapterLabel && (
            <>
              <span>•</span>
              <span>{chapterLabel}</span>
            </>
          )}
          {overallComplexity && (
            <>
              <span>•</span>
              <span>Section Complexity: {overallComplexity}</span>
            </>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div className="mb-3">
        <span className="text-xs font-semibold text-slate-600 block mb-1">Explanation:</span>
        <p className="text-sm text-slate-700">{explanation}</p>
      </div>

      {/* Implementation Approach */}
      <div className="mb-3">
        <span className="text-xs font-semibold text-slate-600 block mb-1">Implementation Approach:</span>
        <div className="bg-white/50 p-3 rounded border border-slate-200">
          <p className="text-sm text-slate-700">{implementationApproach}</p>
        </div>
      </div>

      {/* Matched Phrases */}
      {matchedPhrases.length > 0 && (
        <div className="mb-3">
          <MatchedPhraseChips phrases={matchedPhrases} showLabel={true} />
        </div>
      )}

      {/* View Section Link */}
      <div className="mt-4 pt-3 border-t border-slate-200">
        <Link
          href={`/section/${sectionId}#indicator-${id}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:text-teal-900"
        >
          View in Section <ExternalLink size={14} />
        </Link>
      </div>
    </div>
  );
}
