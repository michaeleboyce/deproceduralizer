'use client';

import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import BookmarkButton from './BookmarkButton';
import FeedbackButton from './FeedbackButton';
import MatchedPhraseChips from './MatchedPhraseChips';

interface AnachronismIndicatorCardProps {
  id: number;
  category: string;
  severity: string;
  modernEquivalent: string | null;
  recommendation: string;
  explanation: string;
  matchedPhrases: string[];
  // Section context
  sectionId: string;
  citation: string;
  heading: string;
  titleLabel: string;
  chapterLabel: string;
  // Parent analysis
  overallSeverity: string | null;
  requiresImmediateReview: boolean;
  summary: string | null;
}

export default function AnachronismIndicatorCard({
  id,
  category,
  severity,
  modernEquivalent,
  recommendation,
  explanation,
  matchedPhrases,
  sectionId,
  citation,
  heading,
  titleLabel,
  chapterLabel,
  overallSeverity,
  requiresImmediateReview,
}: AnachronismIndicatorCardProps) {
  function getSeverityColor(level: string) {
    switch (level) {
      case 'CRITICAL':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          badge: 'bg-red-600',
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-50',
          border: 'border-orange-200',
          badge: 'bg-orange-600',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          badge: 'bg-yellow-600',
        };
      case 'LOW':
        return {
          bg: 'bg-slate-50',
          border: 'border-slate-200',
          badge: 'bg-slate-600',
        };
      default:
        return {
          bg: 'bg-slate-50',
          border: 'border-slate-200',
          badge: 'bg-slate-600',
        };
    }
  }

  function getRecommendationColor(rec: string) {
    switch (rec) {
      case 'REPEAL':
        return 'bg-red-100 text-red-700';
      case 'UPDATE':
        return 'bg-blue-100 text-blue-700';
      case 'REVIEW':
        return 'bg-yellow-100 text-yellow-700';
      case 'PRESERVE':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  }

  function formatCategory(cat: string): string {
    return cat
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  const colors = getSeverityColor(severity);

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} p-6 hover:shadow-md transition-shadow`}>
      {/* Header with badges and action buttons */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex flex-wrap gap-2">
          <span className={`inline-block px-3 py-1 ${colors.badge} text-white text-xs font-bold rounded`}>
            {severity}
          </span>
          <span className="inline-block px-2 py-1 bg-slate-200 text-slate-700 text-xs font-medium rounded">
            {formatCategory(category)}
          </span>
          <span className={`inline-block px-2 py-1 text-xs font-bold rounded ${getRecommendationColor(recommendation)}`}>
            {recommendation}
          </span>
          {requiresImmediateReview && (
            <span className="inline-block px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded">
              Immediate Review Required
            </span>
          )}
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <FeedbackButton
            itemType="anachronism_indicator"
            itemId={id.toString()}
          />
          <BookmarkButton
            itemType="anachronism_indicator"
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
          {overallSeverity && (
            <>
              <span>•</span>
              <span>Section Severity: {overallSeverity}</span>
            </>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div className="mb-3">
        <span className="text-xs font-semibold text-slate-600 block mb-1">Explanation:</span>
        <p className="text-sm text-slate-700">{explanation}</p>
      </div>

      {/* Modern Equivalent */}
      {modernEquivalent && (
        <div className="mb-3">
          <span className="text-xs font-semibold text-slate-600 block mb-1">Modern Equivalent:</span>
          <div className="bg-white/50 p-3 rounded border border-slate-200">
            <p className="text-sm text-slate-700">{modernEquivalent}</p>
          </div>
        </div>
      )}

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
