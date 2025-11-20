'use client';

/**
 * Simple hash function to create consistent IDs for phrases (matches highlight.ts)
 */
function hashString(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Scrolls to and briefly highlights a phrase in the section text
 */
function scrollToPhrase(phrase: string) {
  const phraseHash = hashString(phrase.toLowerCase());
  const dataId = `phrase-${phraseHash}-0`; // Scroll to first occurrence
  const element = document.querySelector(`[data-phrase-id="${dataId}"]`);

  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Add temporary highlight animation
    element.classList.add('ring-2', 'ring-yellow-400', 'ring-offset-1');
    setTimeout(() => {
      element.classList.remove('ring-2', 'ring-yellow-400', 'ring-offset-1');
    }, 2000);
  }
}

interface MatchedPhraseChipsProps {
  phrases: string[];
  showLabel?: boolean;
}

export default function MatchedPhraseChips({ phrases, showLabel = true }: MatchedPhraseChipsProps) {
  if (phrases.length === 0) {
    return null;
  }

  return (
    <div className="mb-3">
      {showLabel && (
        <span className="text-xs font-semibold text-slate-600 block mb-1">
          Matched Phrases (click to scroll):
        </span>
      )}
      <div className="flex flex-wrap gap-1">
        {phrases.map((phrase, phraseIdx) => (
          <button
            key={phraseIdx}
            onClick={() => scrollToPhrase(phrase)}
            className="inline-block px-2 py-0.5 bg-yellow-100 text-yellow-900 text-xs rounded border border-yellow-300 cursor-pointer hover:bg-yellow-200 hover:border-yellow-400 transition-colors"
            title="Click to scroll to this phrase in the section text"
          >
            &ldquo;{phrase}&rdquo;
          </button>
        ))}
      </div>
    </div>
  );
}
