'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  itemType: 'anachronism_indicator' | 'implementation_indicator' | 'similarity_classification';
  itemId: string;
  existingFeedback?: {
    rating: string;
    comment: string;
    suggestedCategory?: string;
    suggestedSeverity?: string;
    suggestedComplexity?: string;
  } | null;
  onSuccess?: () => void;
}

const RATING_OPTIONS = [
  {
    value: 'correct',
    label: 'Correct',
    description: 'Finding is accurate and helpful',
    color: 'green',
  },
  {
    value: 'false_positive',
    label: 'False Positive',
    description: 'Finding is incorrect or not applicable',
    color: 'red',
  },
  {
    value: 'wrong_category',
    label: 'Wrong Category',
    description: 'Finding is valid but miscategorized',
    color: 'yellow',
  },
  {
    value: 'wrong_severity',
    label: 'Wrong Severity/Complexity',
    description: 'Severity or complexity level is incorrect',
    color: 'orange',
  },
  {
    value: 'missing_context',
    label: 'Missing Context',
    description: 'Needs more context or explanation',
    color: 'blue',
  },
  {
    value: 'needs_refinement',
    label: 'Needs Refinement',
    description: 'Generally correct but needs improvement',
    color: 'purple',
  },
];

export default function FeedbackModal({
  isOpen,
  onClose,
  itemType,
  itemId,
  existingFeedback,
  onSuccess,
}: FeedbackModalProps) {
  const [rating, setRating] = useState('');
  const [comment, setComment] = useState('');
  const [suggestedCategory, setSuggestedCategory] = useState('');
  const [suggestedSeverity, setSuggestedSeverity] = useState('');
  const [suggestedComplexity, setSuggestedComplexity] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [reviewerName, setReviewerName] = useState('');
  const [reviewerId, setReviewerId] = useState('');

  // Load reviewer info from localStorage
  useEffect(() => {
    const storedName = localStorage.getItem('reviewerName') || '';
    const storedId = localStorage.getItem('reviewerId') || '';
    setReviewerName(storedName);
    setReviewerId(storedId);
  }, []);

  // Load existing feedback if editing
  useEffect(() => {
    if (existingFeedback) {
      setRating(existingFeedback.rating);
      setComment(existingFeedback.comment);
      setSuggestedCategory(existingFeedback.suggestedCategory || '');
      setSuggestedSeverity(existingFeedback.suggestedSeverity || '');
      setSuggestedComplexity(existingFeedback.suggestedComplexity || '');
    } else {
      // Reset form for new feedback
      setRating('');
      setComment('');
      setSuggestedCategory('');
      setSuggestedSeverity('');
      setSuggestedComplexity('');
    }
  }, [existingFeedback, isOpen]);

  async function handleSubmit() {
    // Validate required fields
    if (!rating || !comment.trim()) {
      alert('Please select a rating and provide a comment.');
      return;
    }

    if (!reviewerId || !reviewerName) {
      alert('Please set your reviewer name first.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          itemType,
          itemId,
          reviewerId,
          reviewerName,
          rating,
          comment: comment.trim(),
          suggestedCategory: suggestedCategory.trim() || null,
          suggestedSeverity: suggestedSeverity || null,
          suggestedComplexity: suggestedComplexity || null,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('Failed to save feedback:', error);
        alert('Failed to save feedback. Please try again.');
        return;
      }

      onSuccess?.();
      onClose();
    } catch (error) {
      console.error('Error saving feedback:', error);
      alert('Error saving feedback. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  function getColorClasses(color: string, selected: boolean) {
    const baseClasses = 'border-2 transition-colors';
    if (selected) {
      switch (color) {
        case 'green':
          return `${baseClasses} border-green-500 bg-green-50`;
        case 'red':
          return `${baseClasses} border-red-500 bg-red-50`;
        case 'yellow':
          return `${baseClasses} border-yellow-500 bg-yellow-50`;
        case 'orange':
          return `${baseClasses} border-orange-500 bg-orange-50`;
        case 'blue':
          return `${baseClasses} border-blue-500 bg-blue-50`;
        case 'purple':
          return `${baseClasses} border-purple-500 bg-purple-50`;
        default:
          return `${baseClasses} border-teal-500 bg-teal-50`;
      }
    }
    return `${baseClasses} border-slate-200 bg-white hover:border-slate-300`;
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">
            {existingFeedback ? 'Update Feedback' : 'Provide Feedback'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded transition-colors"
          >
            <X size={20} className="text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Reviewer Identity */}
          {!(reviewerId && reviewerName) && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-amber-900 mb-2">
                Set Your Reviewer Identity
              </h4>
              <div className="space-y-2">
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => {
                    setReviewerName(e.target.value);
                    localStorage.setItem('reviewerName', e.target.value);
                  }}
                  placeholder="Your name"
                  className="w-full px-3 py-2 border border-amber-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-900 placeholder:text-slate-400"
                />
                <input
                  type="email"
                  value={reviewerId}
                  onChange={(e) => {
                    setReviewerId(e.target.value);
                    localStorage.setItem('reviewerId', e.target.value);
                  }}
                  placeholder="Your email (used as ID)"
                  className="w-full px-3 py-2 border border-amber-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-900 placeholder:text-slate-400"
                />
              </div>
            </div>
          )}

          {/* Rating Selection */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-3">
              Rating <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {RATING_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setRating(option.value)}
                  className={`p-4 rounded-lg text-left ${getColorClasses(
                    option.color,
                    rating === option.value
                  )}`}
                >
                  <div className="font-semibold text-slate-900 mb-1">
                    {option.label}
                  </div>
                  <div className="text-sm text-slate-600">
                    {option.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Comment */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Explanation <span className="text-red-500">*</span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Explain your rating. Be specific about what makes this finding correct or incorrect..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none text-slate-900 placeholder:text-slate-400"
              rows={5}
            />
            <p className="text-xs text-slate-500 mt-1">
              Required. Provide enough detail so others can understand your assessment.
            </p>
          </div>

          {/* Conditional Correction Fields */}
          {rating === 'wrong_category' && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Suggested Category
              </label>
              <input
                type="text"
                value={suggestedCategory}
                onChange={(e) => setSuggestedCategory(e.target.value)}
                placeholder="What should the correct category be?"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 placeholder:text-slate-400"
              />
            </div>
          )}

          {rating === 'wrong_severity' && itemType === 'anachronism_indicator' && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Suggested Severity
              </label>
              <select
                value={suggestedSeverity}
                onChange={(e) => setSuggestedSeverity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 bg-white"
              >
                <option value="">Select severity</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          )}

          {rating === 'wrong_severity' && itemType === 'implementation_indicator' && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Suggested Complexity
              </label>
              <select
                value={suggestedComplexity}
                onChange={(e) => setSuggestedComplexity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 bg-white"
              >
                <option value="">Select complexity</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-6 py-4 flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !rating || !comment.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-teal-700 rounded-lg hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : existingFeedback ? 'Update Feedback' : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </div>
  );
}
