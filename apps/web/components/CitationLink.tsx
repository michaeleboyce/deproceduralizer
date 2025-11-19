'use client';

import React from 'react';
import Link from 'next/link';
import * as HoverCard from '@radix-ui/react-hover-card';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface CitationLinkProps {
  sectionId: string;
  children: React.ReactNode;
  className?: string;
}

export function CitationLink({ sectionId, children, className }: CitationLinkProps) {
  const [previewText, setPreviewText] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleOpenChange = async (open: boolean) => {
    if (open && !previewText && !loading) {
      setLoading(true);
      try {
        // Fetch section preview
        const res = await fetch(`/api/section/${sectionId}`);
        if (res.ok) {
          const data = await res.json();
          setPreviewText(data.heading || 'Section not found');
        } else {
          setPreviewText('Preview unavailable');
        }
      } catch (e) {
        setPreviewText('Error loading preview');
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <HoverCard.Root onOpenChange={handleOpenChange}>
      <HoverCard.Trigger asChild>
        <Link 
          href={`/section/${sectionId}`}
          className={cn(
            "text-teal-600 hover:text-teal-800 hover:underline decoration-teal-300 underline-offset-2 transition-colors",
            className
          )}
        >
          {children}
        </Link>
      </HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content 
          className="z-50 w-80 rounded-md border border-slate-200 bg-white p-4 shadow-md outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          sideOffset={5}
        >
          <div className="flex flex-col gap-2">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {sectionId.replace('dc-', '§ ').replace(/-/g, '.')}
            </div>
            <div className="text-sm text-slate-900">
              {loading ? (
                <span className="animate-pulse text-slate-400">Loading preview...</span>
              ) : (
                previewText
              )}
            </div>
          </div>
          <HoverCard.Arrow className="fill-white" />
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}
