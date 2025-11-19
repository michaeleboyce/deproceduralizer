
export interface Citation {
  text: string;
  sectionId: string;
  type: 'section' | 'range';
}

export function normalizeSectionId(sectionNum: string): string {
  // "1-101" -> "dc-1-101"
  // "1-101.01" -> "dc-1-101-01"
  const normalized = sectionNum.replace(/\./g, '-');
  return `dc-${normalized}`;
}

export function parseCitations(text: string): (string | Citation)[] {
  const parts: (string | Citation)[] = [];
  let lastIndex = 0;

  // Regex for single sections: § 1-101 or section 1-101
  // We'll handle ranges simply by linking the start and end separately for now, 
  // or we can try to parse them. Let's stick to single sections first for robustness.
  // The python regex was: r'§\s*(\d+[-\.]\d+(?:[-\.]\d+)?)'
  
  const regex = /(?:§|section)\s*(\d+[-\.]\d+(?:[-\.]\d+)?)/gi;
  
  let match;
  while ((match = regex.exec(text)) !== null) {
    // Push text before match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const rawText = match[0];
    const sectionNum = match[1];
    
    parts.push({
      text: rawText,
      sectionId: normalizeSectionId(sectionNum),
      type: 'section'
    });

    lastIndex = regex.lastIndex;
  }

  // Push remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}
