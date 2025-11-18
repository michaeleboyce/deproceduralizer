"use client";

import { useState } from "react";
import Link from "next/link";
import SectionDiffModal from "./SectionDiffModal";

interface SimilarSection {
  id: string;
  citation: string;
  heading: string;
  similarity: number;
}

interface SimilarSectionsListProps {
  currentSectionId: string;
  currentSectionCitation: string;
  similarSections: SimilarSection[];
}

export default function SimilarSectionsList({
  currentSectionId,
  currentSectionCitation,
  similarSections,
}: SimilarSectionsListProps) {
  const [diffModalOpen, setDiffModalOpen] = useState(false);
  const [selectedSection, setSelectedSection] =
    useState<SimilarSection | null>(null);

  const handleCompare = (
    section: SimilarSection,
    e: React.MouseEvent<HTMLButtonElement>
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedSection(section);
    setDiffModalOpen(true);
  };

  if (similarSections.length === 0) {
    return null;
  }

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Similar Sections
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Sections with similar content based on semantic analysis
        </p>
        <div className="space-y-3">
          {similarSections.map((similar) => (
            <div
              key={similar.id}
              className="block p-4 bg-indigo-50 border border-indigo-200 rounded-lg"
            >
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={`/section/${similar.id}`}
                  className="flex-1 hover:opacity-80 transition-opacity"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm text-indigo-600 font-medium">
                      {similar.citation}
                    </span>
                    <span className="inline-block px-2 py-0.5 bg-indigo-600 text-white text-xs font-semibold rounded-full">
                      {(similar.similarity * 100).toFixed(1)}% match
                    </span>
                  </div>
                  <p className="text-gray-700 text-sm">{similar.heading}</p>
                </Link>
                <button
                  onClick={(e) => handleCompare(similar, e)}
                  className="flex-shrink-0 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded hover:bg-indigo-700 transition-colors"
                >
                  Compare
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {diffModalOpen && selectedSection && (
        <SectionDiffModal
          section1Id={currentSectionId}
          section1Citation={currentSectionCitation}
          section2Id={selectedSection.id}
          section2Citation={selectedSection.citation}
          onClose={() => setDiffModalOpen(false)}
        />
      )}
    </>
  );
}
