/**
 * Simple hash function to create consistent IDs for phrases
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
 * Highlights specific phrases in HTML text by wrapping them in <mark> tags with unique IDs
 * @param html The HTML text to highlight
 * @param phrases Array of phrases to highlight
 * @returns HTML text with highlighted phrases
 */
export function highlightPhrases(html: string, phrases: string[]): string {
  if (!phrases || phrases.length === 0) {
    return html;
  }

  let result = html;

  // Sort phrases by length (longest first) to avoid highlighting substrings
  const sortedPhrases = [...phrases].sort((a, b) => b.length - a.length);

  // Track occurrence count for each phrase to create unique IDs
  const phraseOccurrences: Record<string, number> = {};

  for (const phrase of sortedPhrases) {
    if (!phrase || phrase.trim().length === 0) {
      continue;
    }

    // Initialize occurrence counter for this phrase
    phraseOccurrences[phrase] = 0;
    const phraseHash = hashString(phrase.toLowerCase());

    // Escape special regex characters in the phrase
    const escapedPhrase = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    // Create regex that matches the phrase (case-insensitive, not inside HTML tags)
    // This regex avoids matching phrases that are inside HTML tags
    const regex = new RegExp(
      `(>[^<]*)(${escapedPhrase})([^<]*<)`,
      "gi"
    );

    // Replace with highlighted version
    result = result.replace(regex, (match, before, phraseMatch, after) => {
      // Only highlight if not already inside a <mark> tag
      if (before.includes("<mark") || after.includes("</mark>")) {
        return match;
      }
      const occurrenceId = phraseOccurrences[phrase]++;
      const dataId = `phrase-${phraseHash}-${occurrenceId}`;
      return `${before}<mark data-phrase-id="${dataId}" class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">${phraseMatch}</mark>${after}`;
    });
  }

  // Also try a simpler approach for phrases in plain text nodes
  for (const phrase of sortedPhrases) {
    if (!phrase || phrase.trim().length === 0) {
      continue;
    }

    const phraseHash = hashString(phrase.toLowerCase());
    const escapedPhrase = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    // Match phrase at word boundaries when not inside tags
    const simpleRegex = new RegExp(
      `(?<![<>])\\b(${escapedPhrase})\\b(?![<>])`,
      "gi"
    );

    result = result.replace(simpleRegex, (match) => {
      // Check if already highlighted
      if (result.includes(`data-phrase-id="phrase-${phraseHash}-`) && result.includes(`>${match}</mark>`)) {
        return match;
      }
      const occurrenceId = phraseOccurrences[phrase]++;
      const dataId = `phrase-${phraseHash}-${occurrenceId}`;
      return `<mark data-phrase-id="${dataId}" class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">${match}</mark>`;
    });
  }

  return result;
}
