'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Code, Wrench, AlertTriangle } from 'lucide-react';

interface PahlkaIndicator {
  id: number;
  category: string;
  complexity: string;
  implementationApproach: string;
  effortEstimate: string | null;
  explanation: string;
  matchedPhrases: string[];
}

interface PahlkaImplementationDisplayProps {
  summary: string | null;
  overallComplexity: string | null;
  requiresTechnicalReview: boolean;
  modelUsed: string | null;
  indicators: PahlkaIndicator[];
}

export default function PahlkaImplementationDisplay({
  summary,
  overallComplexity,
  requiresTechnicalReview,
  modelUsed,
  indicators,
}: PahlkaImplementationDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Helper function to format category names
  const formatCategory = (category: string) => {
    return category
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Helper function to get complexity color
  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'HIGH':
        return {
          bg: 'bg-purple-50',
          border: 'border-purple-200',
          text: 'text-purple-700',
          badge: 'bg-purple-600',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          text: 'text-blue-700',
          badge: 'bg-blue-600',
        };
      case 'LOW':
        return {
          bg: 'bg-indigo-50',
          border: 'border-indigo-200',
          text: 'text-indigo-700',
          badge: 'bg-indigo-600',
        };
      default:
        return {
          bg: 'bg-slate-50',
          border: 'border-slate-200',
          text: 'text-slate-700',
          badge: 'bg-slate-600',
        };
    }
  };

  const overallColors = overallComplexity ? getComplexityColor(overallComplexity) : null;

  return (
    <div
      id="pahlka-implementation"
      className={`rounded-lg border ${overallColors?.border || 'border-slate-200'} shadow-sm p-6 mb-6 scroll-mt-20 ${
        overallColors?.bg || 'bg-white'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Wrench className={overallColors?.text || 'text-slate-700'} size={24} />
            <h2 className="text-xl font-semibold text-slate-900">
              Implementation Analysis
            </h2>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            {overallComplexity && (
              <span className={`inline-block px-3 py-1 ${overallColors?.badge} text-white text-xs font-bold rounded-full`}>
                {overallComplexity} COMPLEXITY
              </span>
            )}
            {requiresTechnicalReview && (
              <span className="inline-block px-3 py-1 bg-orange-600 text-white text-xs font-bold rounded-full flex items-center gap-1">
                <AlertTriangle size={12} />
                TECHNICAL REVIEW REQUIRED
              </span>
            )}
            <span className="inline-block px-2 py-1 bg-slate-200 text-slate-700 text-xs font-medium rounded">
              {indicators.length} {indicators.length === 1 ? 'Issue' : 'Issues'} Identified
            </span>
          </div>

          {/* Summary */}
          {summary && (
            <p className="text-sm text-slate-700 leading-relaxed">
              {summary}
            </p>
          )}
        </div>

        {/* Toggle button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex-shrink-0 ml-4 p-2 hover:bg-white/50 rounded-lg transition-colors"
          aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
        >
          {isExpanded ? (
            <ChevronDown className="text-slate-600" size={20} />
          ) : (
            <ChevronRight className="text-slate-600" size={20} />
          )}
        </button>
      </div>

      {/* Expandable Content */}
      {isExpanded && (
        <>
          {/* Indicators */}
          {indicators.length > 0 && (
            <div className="mt-6 space-y-4">
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                Implementation Issues
              </h3>

              {indicators.map((indicator) => {
                const colors = getComplexityColor(indicator.complexity);
                return (
                  <div
                    key={indicator.id}
                    className={`p-4 rounded-lg border ${colors.border} ${colors.bg}`}
                  >
                    {/* Indicator header */}
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className={`inline-block px-2 py-1 ${colors.badge} text-white text-xs font-bold rounded`}>
                        {indicator.complexity}
                      </span>
                      <span className="inline-block px-2 py-1 bg-slate-200 text-slate-700 text-xs font-medium rounded">
                        {formatCategory(indicator.category)}
                      </span>
                      {indicator.effortEstimate && (
                        <span className="inline-block px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded">
                          Effort: {indicator.effortEstimate}
                        </span>
                      )}
                    </div>

                    {/* Explanation */}
                    <p className="text-sm text-slate-700 mb-3">
                      {indicator.explanation}
                    </p>

                    {/* Implementation Approach */}
                    <div className="mb-3">
                      <span className="text-xs font-semibold text-slate-600 block mb-1">
                        Implementation Approach:
                      </span>
                      <p className="text-sm text-slate-700 bg-white/50 p-2 rounded border border-slate-200">
                        {indicator.implementationApproach}
                      </p>
                    </div>

                    {/* Matched Phrases */}
                    {indicator.matchedPhrases.length > 0 && (
                      <div>
                        <span className="text-xs font-semibold text-slate-600 block mb-1">
                          Matched Phrases:
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {indicator.matchedPhrases.map((phrase, phraseIdx) => (
                            <span
                              key={phraseIdx}
                              className="inline-block px-2 py-0.5 bg-yellow-100 text-yellow-900 text-xs rounded border border-yellow-300"
                            >
                              &ldquo;{phrase}&rdquo;
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Model info */}
          {modelUsed && (
            <div className="mt-4 pt-3 border-t border-slate-300">
              <span className="text-xs text-slate-500">
                Analyzed by: {modelUsed}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
