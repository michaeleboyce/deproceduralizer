'use client';

import React, { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';

// Dynamically import ForceGraph2D with no SSR
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-full bg-slate-50 text-slate-400">Loading Graph...</div>
});

interface GraphData {
  nodes: { id: string; label: string; title: string; group: string; val: number }[];
  links: { source: string; target: string }[];
}

interface CitationGraphProps {
  sectionId?: string;
}

export default function CitationGraph({ sectionId }: CitationGraphProps) {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const url = sectionId 
          ? `/api/graph?centerId=${sectionId}&limit=50` 
          : '/api/graph?limit=200';
        const res = await fetch(url);
        const graphData = await res.json();
        setData(graphData);
      } catch (error) {
        console.error("Failed to fetch graph data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div ref={containerRef} className="w-full h-[600px] border border-slate-200 rounded-lg overflow-hidden bg-slate-50 relative">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10 bg-white/80">
          <span className="text-slate-500 animate-pulse">Loading visualization...</span>
        </div>
      )}
      {!loading && (
        <ForceGraph2D
          width={containerRef.current?.clientWidth || 800}
          height={600}
          graphData={data}
          nodeLabel={(node: any) => `${node.label}: ${node.title}`}
          nodeColor={(node: any) => {
            // Simple color hashing based on group (Title)
            const hash = node.group.split('').reduce((acc: number, char: string) => char.charCodeAt(0) + ((acc << 5) - acc), 0);
            const hue = Math.abs(hash % 360);
            return `hsl(${hue}, 70%, 50%)`;
          }}
          linkColor={() => '#cbd5e1'} // slate-300
          nodeRelSize={6}
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          onNodeClick={(node: any) => {
            router.push(`/section/${node.id}`);
          }}
          cooldownTicks={100}
        />
      )}
    </div>
  );
}
