'use client';

import React, { useState } from 'react';
import parse, { DOMNode, Element } from 'html-react-parser';
import { parseCitations } from '@/lib/citation';
import { CitationLink } from './CitationLink';

interface SubsectionNode {
  level: number;
  label: string;
  content: string;
  children: SubsectionNode[];
}

/**
 * Identifies the hierarchical level based on the subsection marker
 */
function getSubsectionLevel(marker: string): number | null {
  if (/^\([a-z](-\d+)?\)$/.test(marker)) return 1; // (a), (b), (a-1), etc.
  if (/^\(\d+\)$/.test(marker)) return 2; // (1), (2), (3), etc.
  if (/^\([A-Z]\)$/.test(marker)) return 3; // (A), (B), (C), etc.
  if (/^\((i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})\)$/.test(marker)) return 4; // (i), (ii), (iii), etc.
  return null;
}

/**
 * Splits text by subsection markers, keeping the markers
 */
function splitBySubsections(text: string): Array<{ marker: string | null; text: string }> {
  // Pattern matches subsection markers - simplified to just find the markers
  const pattern = /(\([a-z](-\d+)?\)|\(\d+\)|\([A-Z]\)|\((i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})\))\s+/g;

  const segments: Array<{ marker: string | null; text: string }> = [];
  let lastIndex = 0;
  let match;

  // Find all subsection markers
  while ((match = pattern.exec(text)) !== null) {
    const marker = match[1];
    const markerStart = match.index;
    const markerEnd = match.index + match[0].length;

    // Only treat as a subsection marker if it's at the start or preceded by whitespace/punctuation
    const charBefore = markerStart > 0 ? text[markerStart - 1] : '';
    const isValidMarker = markerStart === 0 || /[\s:;,.]/.test(charBefore);

    if (!isValidMarker) {
      continue; // Skip markers that appear mid-word
    }

    // If there's text before this marker, add it as content for the previous section
    if (lastIndex < markerStart) {
      const precedingText = text.slice(lastIndex, markerStart).trim();
      if (precedingText) {
        // Remove trailing punctuation that might separate subsections
        const cleanText = precedingText.replace(/[:;,]\s*$/, '').trim();
        if (cleanText) {
          // Add to the last segment if it exists, otherwise create a new one
          if (segments.length > 0) {
            segments[segments.length - 1].text += ' ' + cleanText;
          } else {
            segments.push({ marker: null, text: cleanText });
          }
        }
      }
    }

    // Start a new segment for this marker
    lastIndex = markerEnd;
    segments.push({ marker, text: '' });
  }

  // Add any remaining text to the last segment
  if (lastIndex < text.length) {
    const remainingText = text.slice(lastIndex).trim();
    if (remainingText) {
      if (segments.length > 0) {
        segments[segments.length - 1].text += remainingText;
      } else {
        segments.push({ marker: null, text: remainingText });
      }
    }
  }

  return segments.filter(seg => seg.marker !== null || seg.text.length > 0);
}

/**
 * Builds a hierarchical tree from flat segments
 */
function buildTree(segments: Array<{ marker: string | null; text: string }>): SubsectionNode[] {
  const root: SubsectionNode[] = [];
  const stack: SubsectionNode[] = [];

  for (const segment of segments) {
    if (!segment.marker) {
      // Text without a marker - add to previous node or skip
      if (stack.length > 0) {
        stack[stack.length - 1].content += ' ' + segment.text;
      }
      continue;
    }

    const level = getSubsectionLevel(segment.marker);
    if (level === null) continue;

    const node: SubsectionNode = {
      level,
      label: segment.marker,
      content: segment.text,
      children: [],
    };

    // Pop stack until we find the appropriate parent
    while (stack.length > 0 && stack[stack.length - 1].level >= level) {
      stack.pop();
    }

    // Add to parent or root
    if (stack.length === 0) {
      root.push(node);
    } else {
      stack[stack.length - 1].children.push(node);
    }

    stack.push(node);
  }

  return root;
}

/**
 * Parses HTML content and builds a hierarchical tree of subsections
 */
function parseSubsections(htmlContent: string): SubsectionNode[] {
  let allSegments: Array<{ marker: string | null; text: string }> = [];

  // Extract text from all paragraphs
  parse(htmlContent, {
    replace: (domNode: DOMNode) => {
      if (domNode.type === 'tag' && domNode.name === 'p') {
        const element = domNode as Element;
        const textContent = getTextContent(element);
        if (textContent) {
          const segments = splitBySubsections(textContent);
          allSegments = allSegments.concat(segments);
        }
      }
    },
  });

  return buildTree(allSegments);
}

/**
 * Gets text content from an Element node
 */
function getTextContent(element: Element): string {
  let text = '';

  function traverse(node: any) {
    if (node.type === 'text') {
      text += node.data;
    } else if (node.children) {
      node.children.forEach(traverse);
    }
  }

  traverse(element);
  return text.trim();
}

/**
 * Renders a single subsection node with its children
 */
function SubsectionNodeRenderer({
  node,
  depth = 0,
  parentPath = ''
}: {
  node: SubsectionNode;
  depth?: number;
  parentPath?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(depth < 2); // Auto-expand first 2 levels
  const [showCopied, setShowCopied] = useState(false);
  const hasChildren = node.children.length > 0;

  // Create unique anchor ID based on the full path
  const currentPath = parentPath ? `${parentPath}-${node.label}` : node.label;
  const anchorId = currentPath.replace(/[()]/g, '').replace(/\s+/g, '-');

  // Progressive indentation based on depth
  const indentationClasses = [
    '',           // Level 0 (depth 0): no indent
    'ml-6',       // Level 1 (depth 1): 24px
    'ml-12',      // Level 2 (depth 2): 48px
    'ml-16',      // Level 3 (depth 3): 64px
  ];
  const indentClass = indentationClasses[depth] || 'ml-20';

  // Color scheme for different levels
  const levelColors = [
    'border-l-4 border-teal-500 bg-teal-50/50',    // Level 1: (a), (b), (c)
    'border-l-4 border-blue-500 bg-blue-50/50',     // Level 2: (1), (2), (3)
    'border-l-4 border-purple-500 bg-purple-50/50', // Level 3: (A), (B), (C)
    'border-l-4 border-slate-400 bg-slate-50/50',   // Level 4: (i), (ii), (iii)
  ];

  const labelColors = [
    'text-teal-800 font-bold',      // Level 1
    'text-blue-800 font-semibold',  // Level 2
    'text-purple-800 font-semibold', // Level 3
    'text-slate-700 font-medium',   // Level 4
  ];

  const colorClass = levelColors[node.level - 1] || 'border-l-4 border-gray-300 bg-gray-50/50';
  const labelColorClass = labelColors[node.level - 1] || 'text-gray-700 font-medium';

  // Handle anchor link copy
  const handleCopyLink = () => {
    const url = `${window.location.origin}${window.location.pathname}#${anchorId}`;
    navigator.clipboard.writeText(url);
    setShowCopied(true);
    setTimeout(() => setShowCopied(false), 2000);
  };

  // Parse citations in content
  const renderContent = () => {
    const parts = parseCitations(node.content);
    if (parts.length === 1 && typeof parts[0] === 'string') {
      return node.content;
    }
    return (
      <>
        {parts.map((part, i) => {
          if (typeof part === 'string') return part;
          return (
            <CitationLink key={i} sectionId={part.sectionId}>
              {part.text}
            </CitationLink>
          );
        })}
      </>
    );
  };

  return (
    <div
      id={anchorId}
      className={`${depth > 0 ? `${indentClass} mt-3` : 'mb-4'} scroll-mt-24 group`}
    >
      <div className={`rounded-lg p-4 ${colorClass} shadow-sm hover:shadow-md transition-shadow`}>
        <div className="flex gap-3 items-start">
          {/* Subsection label with anchor link */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`font-mono text-base ${labelColorClass}`}>
              {node.label}
            </span>
            <button
              onClick={handleCopyLink}
              className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-600"
              title="Copy link to this subsection"
            >
              {showCopied ? (
                <span className="text-xs text-green-600">✓</span>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              )}
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="text-slate-700 text-sm leading-relaxed">
              {renderContent()}
            </div>

            {/* Toggle button for children */}
            {hasChildren && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-3 px-3 py-1.5 text-xs font-medium rounded-md transition-all
                           bg-white/60 hover:bg-white border border-slate-300 hover:border-slate-400
                           text-slate-600 hover:text-slate-800 shadow-sm hover:shadow"
              >
                {isExpanded ? (
                  <>
                    <span className="inline-block mr-1.5">▼</span>
                    Hide {node.children.length} subsection{node.children.length > 1 ? 's' : ''}
                  </>
                ) : (
                  <>
                    <span className="inline-block mr-1.5">▶</span>
                    Show {node.children.length} subsection{node.children.length > 1 ? 's' : ''}
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Children */}
        {hasChildren && isExpanded && (
          <div className="mt-3 space-y-2 pl-2">
            {node.children.map((child, index) => (
              <SubsectionNodeRenderer
                key={index}
                node={child}
                depth={depth + 1}
                parentPath={currentPath}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Main component that parses and displays section text with hierarchical subsections
 */
export default function SubsectionParser({ htmlContent }: { htmlContent: string }) {
  const subsections = parseSubsections(htmlContent);

  // If no subsections were found, fall back to regular rendering
  if (subsections.length === 0) {
    return (
      <div className="prose prose-sm max-w-none text-slate-700 leading-relaxed">
        {parse(htmlContent, {
          replace: (domNode: DOMNode) => {
            if (domNode.type === 'text' && 'data' in domNode && typeof domNode.data === 'string') {
              const parts = parseCitations(domNode.data);
              if (parts.length === 1 && typeof parts[0] === 'string') {
                return domNode.data;
              }
              return (
                <>
                  {parts.map((part, i) => {
                    if (typeof part === 'string') return part;
                    return (
                      <CitationLink key={i} sectionId={part.sectionId}>
                        {part.text}
                      </CitationLink>
                    );
                  })}
                </>
              );
            }
          },
        })}
      </div>
    );
  }

  // Render hierarchical subsections
  return (
    <div className="space-y-4">
      {subsections.map((node, index) => (
        <SubsectionNodeRenderer key={index} node={node} depth={0} parentPath="" />
      ))}
    </div>
  );
}
