'use client';

import { useState, useEffect } from 'react';
import { Bookmark, BookmarkCheck } from 'lucide-react';

interface BookmarkButtonProps {
  itemType: 'section' | 'conflict' | 'duplicate' | 'reporting' | 'anachronism' | 'implementation';
  itemId: string;
  onBookmarkChange?: (isBookmarked: boolean) => void;
}

export default function BookmarkButton({ itemType, itemId, onBookmarkChange }: BookmarkButtonProps) {
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [bookmarkId, setBookmarkId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [note, setNote] = useState('');

  // Check if item is already bookmarked on mount
  useEffect(() => {
    checkIfBookmarked();
  }, [itemType, itemId]);

  async function checkIfBookmarked() {
    try {
      const response = await fetch(`/api/bookmarks?itemType=${itemType}`);
      if (!response.ok) return;

      const data = await response.json();
      const existingBookmark = data.bookmarks?.find(
        (b: any) => b.itemId === itemId && b.itemType === itemType
      );

      if (existingBookmark) {
        setIsBookmarked(true);
        setBookmarkId(existingBookmark.id);
        setNote(existingBookmark.note || '');
      }
    } catch (error) {
      console.error('Error checking bookmark status:', error);
    }
  }

  async function handleBookmarkClick() {
    if (isBookmarked) {
      // Show confirmation modal before removing
      setShowDeleteModal(true);
    } else {
      // Show modal to add bookmark with optional note
      setShowNoteModal(true);
    }
  }

  async function addBookmark() {
    setIsLoading(true);
    try {
      const response = await fetch('/api/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          itemType,
          itemId,
          note: note.trim() || null,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('Failed to add bookmark:', error);
        return;
      }

      const data = await response.json();
      setIsBookmarked(true);
      setBookmarkId(data.bookmark.id);
      setShowNoteModal(false);
      onBookmarkChange?.(true);
    } catch (error) {
      console.error('Error adding bookmark:', error);
    } finally {
      setIsLoading(false);
    }
  }

  async function removeBookmark() {
    if (!bookmarkId) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        console.error('Failed to remove bookmark');
        return;
      }

      setIsBookmarked(false);
      setBookmarkId(null);
      setNote('');
      setShowDeleteModal(false);
      onBookmarkChange?.(false);
    } catch (error) {
      console.error('Error removing bookmark:', error);
    } finally {
      setIsLoading(false);
    }
  }

  function formatItemType(type: string): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  async function updateNote() {
    if (!bookmarkId) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/api/bookmarks/${bookmarkId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: note.trim() || null }),
      });

      if (!response.ok) {
        console.error('Failed to update note');
        return;
      }

      setShowNoteModal(false);
    } catch (error) {
      console.error('Error updating note:', error);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={handleBookmarkClick}
        disabled={isLoading}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors ${
          isBookmarked
            ? 'bg-amber-50 border-amber-300 text-amber-700 hover:bg-amber-100'
            : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50'
        } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        title={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
      >
        {isBookmarked ? (
          <BookmarkCheck size={16} className="text-amber-600" />
        ) : (
          <Bookmark size={16} />
        )}
        <span className="text-sm font-medium">
          {isBookmarked ? 'Bookmarked' : 'Bookmark'}
        </span>
      </button>

      {/* Add/Edit note button when bookmarked */}
      {isBookmarked && (
        <button
          onClick={() => setShowNoteModal(true)}
          className="ml-2 text-xs text-slate-600 hover:text-slate-900 underline"
        >
          {note ? 'Edit note' : 'Add note'}
        </button>
      )}

      {/* Note Modal */}
      {showNoteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              {isBookmarked ? 'Edit Bookmark Note' : 'Add Bookmark'}
            </h3>

            <label className="block mb-4">
              <span className="text-sm font-medium text-slate-700 mb-1 block">
                Note (optional)
              </span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add a note about why you bookmarked this..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
                rows={4}
              />
            </label>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowNoteModal(false);
                  if (!isBookmarked) {
                    setNote('');
                  }
                }}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={isBookmarked ? updateNote : addBookmark}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-teal-700 rounded-lg hover:bg-teal-800 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">
              Remove Bookmark?
            </h3>

            <div className="mb-6">
              <p className="text-slate-700 mb-3">
                Are you sure you want to remove this bookmark?
              </p>

              <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-slate-600">Type:</span>
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded">
                    {formatItemType(itemType)}
                  </span>
                </div>
                <div className="mb-2">
                  <span className="text-xs font-semibold text-slate-600">Item ID:</span>
                  <code className="ml-2 text-xs text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded">
                    {itemId}
                  </code>
                </div>
                {note && (
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <span className="text-xs font-semibold text-slate-600 block mb-1">Your Note:</span>
                    <p className="text-sm text-slate-700 italic">&ldquo;{note}&rdquo;</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={removeBookmark}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {isLoading ? 'Removing...' : 'Yes, Remove Bookmark'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
