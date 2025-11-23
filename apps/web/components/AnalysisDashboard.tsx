'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowRight, Copy } from 'lucide-react';
import FeedbackButton from './FeedbackButton';
import BookmarkButton from './BookmarkButton';

interface Conflict {
  sectionA: string;
  sectionB: string;
  citationA: string;
  citationB: string;
  classification: string;
  explanation: string;
  analyzedAt: string;
}

export default function AnalysisDashboard() {
  const [items, setItems] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'conflicting' | 'duplicate'>('conflicting');

  useEffect(() => {
    const fetchItems = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/conflicts?type=${activeTab}`);
        const data = await res.json();
        setItems(data.conflicts);
      } catch (error) {
        console.error("Failed to fetch items:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchItems();
  }, [activeTab]);

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex space-x-1 bg-slate-100 p-1 rounded-lg inline-flex">
        <button
          onClick={() => setActiveTab('conflicting')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'conflicting'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
          }`}
        >
          Conflicts
        </button>
        <button
          onClick={() => setActiveTab('duplicate')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'duplicate'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
          }`}
        >
          Duplicates
        </button>
      </div>

      {loading ? (
        <div className="p-8 text-center text-slate-500">Loading {activeTab}s...</div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center bg-slate-50 rounded-lg border border-slate-200">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mb-4">
            <span className="text-2xl">✅</span>
          </div>
          <h3 className="text-lg font-medium text-slate-900">No {activeTab}s Detected</h3>
          <p className="text-slate-500 mt-2">The analysis found no {activeTab} sections in the current dataset.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((item, index) => (
            <div key={index} className={`bg-white p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow ${
              activeTab === 'conflicting' ? 'border-red-100' : 'border-amber-100'
            }`}>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 mt-1">
                  {activeTab === 'conflicting' ? (
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                  ) : (
                    <Copy className="w-5 h-5 text-amber-500" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Link href={`/section/${item.sectionA}`} className="font-mono font-medium text-slate-900 hover:underline">
                      {item.citationA || item.sectionA}
                    </Link>
                    <ArrowRight className="w-4 h-4 text-slate-400" />
                    <Link href={`/section/${item.sectionB}`} className="font-mono font-medium text-slate-900 hover:underline">
                      {item.citationB || item.sectionB}
                    </Link>
                    <span className={`text-xs font-medium px-2 py-1 rounded-full uppercase tracking-wide ${
                      activeTab === 'conflicting'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}>
                      {item.classification}
                    </span>
                    <div className="ml-auto flex gap-2 flex-shrink-0">
                      <FeedbackButton
                        itemType="similarity_classification"
                        itemId={`${item.sectionA}:${item.sectionB}`}
                      />
                      <BookmarkButton
                        itemType={activeTab}
                        itemId={`${item.sectionA}:${item.sectionB}`}
                      />
                    </div>
                  </div>
                  <p className="text-slate-700 text-sm leading-relaxed bg-slate-50 p-3 rounded border border-slate-100">
                    {item.explanation}
                  </p>
                  <div className="mt-3 text-xs text-slate-400">
                    Detected by AI analysis on {new Date(item.analyzedAt).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
