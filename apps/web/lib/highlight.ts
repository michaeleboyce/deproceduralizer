/**
 * Highlights specific phrases in HTML text by wrapping them in <mark> tags
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

  for (const phrase of sortedPhrases) {
    if (!phrase || phrase.trim().length === 0) {
      continue;
    }

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
      return `${before}<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">${phraseMatch}</mark>${after}`;
    });
  }

  // Also try a simpler approach for phrases in plain text nodes
  for (const phrase of sortedPhrases) {
    if (!phrase || phrase.trim().length === 0) {
      continue;
    }

    const escapedPhrase = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    // Match phrase at word boundaries when not inside tags
    const simpleRegex = new RegExp(
      `(?<![<>])\\b(${escapedPhrase})\\b(?![<>])`,
      "gi"
    );

    result = result.replace(simpleRegex, (match) => {
      // Check if already highlighted
      if (result.includes(`<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">${match}</mark>`)) {
        return match;
      }
      return `<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">${match}</mark>`;
    });
  }

  return result;
}
