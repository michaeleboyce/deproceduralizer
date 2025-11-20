'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Navigation from '@/components/Navigation';
import { Bookmark, Trash2, Edit3, ExternalLink } from 'lucide-react';

interface Bookmark {
  id: number;
  jurisdiction: string;
  itemType: 'section' | 'conflict' | 'duplicate' | 'reporting' | 'anachronism' | 'implementation';
  itemId: string;
  note: string | null;
  createdAt: string;
  updatedAt: string;
}

export default function BookmarksPage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  // Edit note state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNote, setEditNote] = useState('');

  useEffect(() => {
    fetchBookmarks();
  }, []);

  async function fetchBookmarks() {
    setLoading(true);
    try {
      const response = await fetch('/api/bookmarks');
      if (!response.ok) throw new Error('Failed to fetch bookmarks');

      const data = await response.json();
      setBookmarks(data.bookmarks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  async function deleteBookmark(id: number) {
    if (!confirm('Are you sure you want to remove this bookmark?')) return;

    try {
      const response = await fetch(`/api/bookmarks/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete bookmark');

      setBookmarks(bookmarks.filter(b => b.id !== id));
    } catch (err) {
      alert('Failed to delete bookmark');
      console.error(err);
    }
  }

  async function updateNote(id: number, note: string) {
    try {
      const response = await fetch(`/api/bookmarks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: note.trim() || null }),
      });

      if (!response.ok) throw new Error('Failed to update note');

      const data = await response.json();
      setBookmarks(bookmarks.map(b => b.id === id ? data.bookmark : b));
      setEditingId(null);
      setEditNote('');
    } catch (err) {
      alert('Failed to update note');
      console.error(err);
    }
  }

  function startEditing(bookmark: Bookmark) {
    setEditingId(bookmark.id);
    setEditNote(bookmark.note || '');
  }

  function cancelEditing() {
    setEditingId(null);
    setEditNote('');
  }

  function getItemLink(bookmark: Bookmark): string {
    switch (bookmark.itemType) {
      case 'section':
        return `/section/${bookmark.itemId}`;
      case 'reporting':
        return `/section/${bookmark.itemId}#reporting`;
      case 'anachronism':
        return `/section/${bookmark.itemId}#anachronisms`;
      case 'implementation':
        return `/section/${bookmark.itemId}#pahlka-implementation`;
      case 'conflict':
      case 'duplicate':
        // itemId format: "sectionA:sectionB"
        const [sectionA] = bookmark.itemId.split(':');
        return `/dashboard/conflicts?highlight=${bookmark.itemId}`;
      default:
        return '/';
    }
  }

  function formatItemType(type: string): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  function getItemTypeBadgeColor(type: string): string {
    switch (type) {
      case 'section':
        return 'bg-teal-100 text-teal-700';
      case 'reporting':
        return 'bg-violet-100 text-violet-700';
      case 'anachronism':
        return 'bg-red-100 text-red-700';
      case 'implementation':
        return 'bg-purple-100 text-purple-700';
      case 'conflict':
        return 'bg-orange-100 text-orange-700';
      case 'duplicate':
        return 'bg-yellow-100 text-yellow-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  }

  const filteredBookmarks = filterType === 'all'
    ? bookmarks
    : bookmarks.filter(b => b.itemType === filterType);

  const itemTypes = ['all', 'section', 'reporting', 'anachronism', 'implementation', 'conflict', 'duplicate'];
  const typeCounts = itemTypes.reduce((acc, type) => {
    acc[type] = type === 'all' ? bookmarks.length : bookmarks.filter(b => b.itemType === type).length;
    return acc;
  }, {} as Record<string, number>);

  return (
    <>
      <Navigation breadcrumbs={[
        { label: 'Home', href: '/' },
        { label: 'Bookmarks' }
      ]} />

      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <Bookmark className="text-amber-600" size={32} />
              <h1 className="text-3xl font-bold text-slate-900">Bookmarks</h1>
            </div>
            <p className="text-slate-600">
              Your saved sections, reports, anachronisms, and implementation analyses
            </p>
          </div>

          {/* Filter Tabs */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 mb-6">
            <div className="flex flex-wrap gap-2">
              {itemTypes.map(type => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    filterType === type
                      ? 'bg-teal-700 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {formatItemType(type)} ({typeCounts[type] || 0})
                </button>
              ))}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-12">
              <p className="text-slate-500">Loading bookmarks...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
              <p className="text-red-700">Error: {error}</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredBookmarks.length === 0 && (
            <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
              <Bookmark className="mx-auto mb-4 text-slate-300" size={48} />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                No bookmarks yet
              </h3>
              <p className="text-slate-600">
                {filterType === 'all'
                  ? 'Start bookmarking sections, reports, and analyses as you browse'
                  : `No ${filterType} bookmarks found`
                }
              </p>
            </div>
          )}

          {/* Bookmarks List */}
          {!loading && !error && filteredBookmarks.length > 0 && (
            <div className="space-y-4">
              {filteredBookmarks.map(bookmark => (
                <div key={bookmark.id} className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {/* Item Type Badge */}
                      <div className="mb-3">
                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getItemTypeBadgeColor(bookmark.itemType)}`}>
                          {formatItemType(bookmark.itemType)}
                        </span>
                      </div>

                      {/* Item ID */}
                      <div className="mb-2">
                        <span className="text-sm font-medium text-slate-700">Item: </span>
                        <code className="text-sm text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                          {bookmark.itemId}
                        </code>
                      </div>

                      {/* Note */}
                      {editingId === bookmark.id ? (
                        <div className="mt-3">
                          <textarea
                            value={editNote}
                            onChange={(e) => setEditNote(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none text-sm"
                            rows={3}
                            placeholder="Add a note..."
                          />
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={() => updateNote(bookmark.id, editNote)}
                              className="px-3 py-1 bg-teal-700 text-white text-sm rounded-lg hover:bg-teal-800"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditing}
                              className="px-3 py-1 bg-slate-200 text-slate-700 text-sm rounded-lg hover:bg-slate-300"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        bookmark.note && (
                          <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                            <p className="text-sm text-slate-700 italic">&ldquo;{bookmark.note}&rdquo;</p>
                          </div>
                        )
                      )}

                      {/* Timestamp */}
                      <div className="mt-3 text-xs text-slate-500">
                        Bookmarked {new Date(bookmark.createdAt).toLocaleDateString()}
                        {bookmark.updatedAt !== bookmark.createdAt && (
                          <> • Updated {new Date(bookmark.updatedAt).toLocaleDateString()}</>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-2">
                      <Link
                        href={getItemLink(bookmark)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-teal-50 text-teal-700 rounded-lg hover:bg-teal-100 text-sm font-medium transition-colors"
                      >
                        View <ExternalLink size={14} />
                      </Link>
                      <button
                        onClick={() => startEditing(bookmark)}
                        disabled={editingId !== null}
                        className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-sm font-medium disabled:opacity-50"
                      >
                        <Edit3 size={14} /> Note
                      </button>
                      <button
                        onClick={() => deleteBookmark(bookmark.id)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 text-sm font-medium"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
