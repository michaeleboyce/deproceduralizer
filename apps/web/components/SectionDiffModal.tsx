"use client";

import { useEffect, useState } from "react";
import DiffMatchPatch from "diff-match-patch";

interface SectionDiffModalProps {
  section1Id: string;
  section1Citation: string;
  section2Id: string;
  section2Citation: string;
  onClose: () => void;
}

interface SectionData {
  id: string;
  citation: string;
  heading: string;
  textPlain: string;
}

export default function SectionDiffModal({
  section1Id,
  section1Citation,
  section2Id,
  section2Citation,
  onClose,
}: SectionDiffModalProps) {
  const [section1, setSection1] = useState<SectionData | null>(null);
  const [section2, setSection2] = useState<SectionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSections = async () => {
      try {
        setLoading(true);
        const [res1, res2] = await Promise.all([
          fetch(`/api/section/${section1Id}`),
          fetch(`/api/section/${section2Id}`),
        ]);

        if (!res1.ok || !res2.ok) {
          throw new Error("Failed to fetch sections");
        }

        const data1 = await res1.json();
        const data2 = await res2.json();

        setSection1(data1);
        setSection2(data2);
      } catch (err) {
        setError("Failed to load sections for comparison");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSections();
  }, [section1Id, section2Id]);

  const renderDiff = () => {
    if (!section1 || !section2) return null;

    const dmp = new DiffMatchPatch();
    const diffs = dmp.diff_main(section1.textPlain, section2.textPlain);
    dmp.diff_cleanupSemantic(diffs);

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">
              {section1.citation}
            </h4>
            <p className="text-sm text-gray-600">{section1.heading}</p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">
              {section2.citation}
            </h4>
            <p className="text-sm text-gray-600">{section2.heading}</p>
          </div>
        </div>

        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 max-h-[60vh] overflow-y-auto">
          <div className="prose prose-sm max-w-none">
            {diffs.map((diff, index) => {
              const [operation, text] = diff;
              if (operation === 0) {
                // No change
                return (
                  <span key={index} className="text-gray-700">
                    {text}
                  </span>
                );
              } else if (operation === -1) {
                // Deleted from section1
                return (
                  <span
                    key={index}
                    className="bg-red-200 text-red-900 line-through"
                  >
                    {text}
                  </span>
                );
              } else {
                // Added in section2
                return (
                  <span key={index} className="bg-green-200 text-green-900">
                    {text}
                  </span>
                );
              }
            })}
          </div>
        </div>

        <div className="flex gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <span className="inline-block w-4 h-4 bg-red-200 border border-red-300 rounded"></span>
            <span>Removed</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="inline-block w-4 h-4 bg-green-200 border border-green-300 rounded"></span>
            <span>Added</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-2xl font-bold text-gray-900">
            Section Comparison
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close modal"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto">
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="text-gray-600 mt-4">Loading sections...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {!loading && !error && renderDiff()}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
