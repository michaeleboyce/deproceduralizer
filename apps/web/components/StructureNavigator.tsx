'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ChevronRight, ChevronDown, Loader2 } from 'lucide-react';

interface StructureNode {
  id: string;
  parent_id: string | null;
  level: string;
  label: string;
  heading: string;
  ordinal: number;
  has_section: boolean;
  section_id: string | null;
  children?: StructureNode[];
}

interface StructureNavigatorProps {
  className?: string;
}

export default function StructureNavigator({ className = '' }: StructureNavigatorProps) {
  const [tree, setTree] = useState<StructureNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch('/api/structure')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setTree(data.tree);
          // Auto-expand top-level nodes (titles)
          const topLevelIds = data.tree.map((node: StructureNode) => node.id);
          setExpanded(new Set(topLevelIds));
        } else {
          setError(data.error || 'Failed to load structure');
        }
      })
      .catch(err => {
        console.error('Error loading structure:', err);
        setError('Failed to load structure');
      })
      .finally(() => setLoading(false));
  }, []);

  const toggleExpanded = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const renderNode = (node: StructureNode, depth: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expanded.has(node.id);
    const paddingLeft = `${depth * 1.25}rem`;

    // Only show "View →" link for nodes that have actual section content
    const linkId = node.section_id || node.id;

    return (
      <div key={node.id} className="select-none">
        <div
          className="flex items-start py-1.5 px-2 hover:bg-slate-50 rounded-sm group transition-colors"
          style={{ paddingLeft }}
        >
          {/* Expand/collapse icon */}
          <button
            onClick={() => hasChildren && toggleExpanded(node.id)}
            className="flex-shrink-0 mt-0.5 mr-1 text-slate-400 hover:text-slate-600"
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )
            ) : (
              <span className="w-4 inline-block" />
            )}
          </button>

          {/* Label and heading */}
          <div className="flex-1 min-w-0 flex items-baseline gap-2">
            <span className={`font-medium text-sm ${
              node.level === 'title' ? 'text-teal-700' :
              node.level === 'chapter' ? 'text-slate-700' :
              'text-slate-600'
            }`}>
              {node.label}
            </span>
            <span className="text-sm text-slate-500 truncate">
              {node.heading}
            </span>
          </div>

          {/* View link - only shown for nodes with actual section content */}
          {node.has_section && (
            <Link
              href={`/section/${linkId}`}
              className="flex-shrink-0 ml-2 px-2 py-0.5 text-xs font-medium text-slate-500
                         hover:text-slate-700 hover:bg-slate-100 rounded opacity-0 group-hover:opacity-100 transition-all"
              onClick={(e) => e.stopPropagation()}
            >
              View →
            </Link>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div>
            {node.children!.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-8 ${className}`}>
        <Loader2 className="animate-spin text-slate-400" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
        <p className="text-red-700">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-slate-200 rounded-lg p-4 ${className}`}>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Browse by Chapter</h2>
      <div className="space-y-0.5">
        {tree.map(node => renderNode(node))}
      </div>
      <div className="mt-4 pt-4 border-t border-slate-200 text-sm text-slate-500">
        {tree.length} titles loaded
      </div>
    </div>
  );
}
