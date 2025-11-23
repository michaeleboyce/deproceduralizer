'use client';

import { useState, useEffect } from 'react';
import { MessageSquare, CheckCircle2, AlertCircle, Edit3 } from 'lucide-react';
import FeedbackModal from './FeedbackModal';

interface FeedbackButtonProps {
  itemType: 'anachronism_indicator' | 'implementation_indicator' | 'similarity_classification';
  itemId: string;
  jurisdiction?: string;
  onFeedbackChange?: (hasFeedback: boolean) => void;
}

export default function FeedbackButton({
  itemType,
  itemId,
  jurisdiction = 'dc',
  onFeedbackChange,
}: FeedbackButtonProps) {
  const [showModal, setShowModal] = useState(false);
  const [existingFeedback, setExistingFeedback] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    checkExistingFeedback();
  }, [itemType, itemId, jurisdiction]);

  async function checkExistingFeedback() {
    try {
      setIsLoading(true);
      const response = await fetch(
        `/api/feedback?itemType=${itemType}&itemId=${itemId}&jurisdiction=${jurisdiction}`
      );

      if (!response.ok) {
        setExistingFeedback(null);
        return;
      }

      const data = await response.json();
      if (data.feedback && data.feedback.length > 0) {
        // Get current reviewer's feedback
        const reviewerId = localStorage.getItem('reviewerId');
        const myFeedback = data.feedback.find(
          (f: any) => f.reviewer_id === reviewerId
        );
        setExistingFeedback(myFeedback || data.feedback[0]); // Fallback to first feedback if not found
      } else {
        setExistingFeedback(null);
      }
    } catch (error) {
      console.error('Error checking feedback:', error);
      setExistingFeedback(null);
    } finally {
      setIsLoading(false);
    }
  }

  function getRatingColor(rating: string) {
    switch (rating) {
      case 'correct':
        return 'text-green-600';
      case 'false_positive':
        return 'text-red-600';
      case 'wrong_category':
        return 'text-yellow-600';
      case 'wrong_severity':
        return 'text-orange-600';
      case 'missing_context':
        return 'text-blue-600';
      case 'needs_refinement':
        return 'text-purple-600';
      default:
        return 'text-slate-600';
    }
  }

  function getRatingIcon(rating: string) {
    switch (rating) {
      case 'correct':
        return <CheckCircle2 size={16} className="text-green-600" />;
      case 'false_positive':
        return <AlertCircle size={16} className="text-red-600" />;
      default:
        return <MessageSquare size={16} className={getRatingColor(rating)} />;
    }
  }

  function getRatingLabel(rating: string) {
    const labels: { [key: string]: string } = {
      correct: 'Correct',
      false_positive: 'False Positive',
      wrong_category: 'Wrong Category',
      wrong_severity: 'Wrong Severity',
      missing_context: 'Missing Context',
      needs_refinement: 'Needs Refinement',
    };
    return labels[rating] || 'Reviewed';
  }

  const hasFeedback = !!existingFeedback;

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        disabled={isLoading}
        className={`relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors ${
          hasFeedback
            ? 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
            : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50'
        } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        title={hasFeedback ? 'Click to edit feedback' : 'Provide feedback'}
      >
        <div className="relative">
          {hasFeedback ? (
            getRatingIcon(existingFeedback.rating)
          ) : (
            <MessageSquare size={16} />
          )}

          {/* Edit indicator for existing feedback */}
          {hasFeedback && (
            <span
              className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-blue-500 rounded-full border border-white flex items-center justify-center shadow-sm transition-transform hover:scale-125 hover:shadow-md"
              title="Has feedback - Click to edit"
            >
              <Edit3 size={9} className="text-white" strokeWidth={3} />
            </span>
          )}
        </div>

        <span className="text-sm font-medium">
          {hasFeedback ? getRatingLabel(existingFeedback.rating) : 'Feedback'}
        </span>

        {/* Show reviewer name on hover if feedback exists */}
        {hasFeedback && isHovered && existingFeedback.reviewer_name && (
          <span className="text-xs text-slate-500 italic ml-1">
            by {existingFeedback.reviewer_name}
          </span>
        )}
      </button>

      <FeedbackModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        itemType={itemType}
        itemId={itemId}
        existingFeedback={
          existingFeedback
            ? {
                rating: existingFeedback.rating,
                comment: existingFeedback.comment,
                suggestedCategory: existingFeedback.suggested_category,
                suggestedSeverity: existingFeedback.suggested_severity,
                suggestedComplexity: existingFeedback.suggested_complexity,
              }
            : null
        }
        onSuccess={() => {
          checkExistingFeedback();
          onFeedbackChange?.(true);
        }}
      />
    </>
  );
}
