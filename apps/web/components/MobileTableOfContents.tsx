"use client";

interface TocItem {
  id: string;
  label: string;
}

interface MobileTableOfContentsProps {
  items: TocItem[];
}

export default function MobileTableOfContents({ items }: MobileTableOfContentsProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // Close the details element after clicking
    const details = e.currentTarget.closest('details');
    if (details) details.removeAttribute('open');
  };

  return (
    <div className="lg:hidden sticky top-0 z-10 bg-white border-b border-slate-200 mb-6 -mx-4 px-4 py-3 shadow-sm">
      <details className="group">
        <summary className="flex items-center justify-between cursor-pointer list-none">
          <span className="text-sm font-semibold text-slate-700">Jump to Section</span>
          <svg
            className="w-5 h-5 text-slate-500 transition-transform group-open:rotate-180"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <nav className="mt-3 space-y-1">
          {items.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="block px-3 py-2 text-sm text-slate-600 hover:text-teal-700 hover:bg-teal-50 rounded-md transition-colors"
              onClick={handleClick}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </details>
    </div>
  );
}
