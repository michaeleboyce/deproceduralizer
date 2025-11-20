"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface Breadcrumb {
  label: string;
  href?: string;
}

interface NavigationProps {
  breadcrumbs?: Breadcrumb[];
}

export default function Navigation({ breadcrumbs }: NavigationProps) {
  const pathname = usePathname();

  // Generate default breadcrumbs if not provided
  const defaultBreadcrumbs = (): Breadcrumb[] => {
    const crumbs: Breadcrumb[] = [{ label: "Home", href: "/" }];

    if (pathname === "/") return [];
    if (pathname === "/search") {
      crumbs.push({ label: "Search" });
    } else if (pathname === "/bookmarks") {
      crumbs.push({ label: "Bookmarks" });
    } else if (pathname === "/reporting") {
      crumbs.push({ label: "Analysis", href: "/dashboard/conflicts" });
      crumbs.push({ label: "Reporting Requirements" });
    } else if (pathname === "/anachronisms") {
      crumbs.push({ label: "Analysis", href: "/dashboard/conflicts" });
      crumbs.push({ label: "Anachronisms" });
    } else if (pathname === "/pahlka-implementations") {
      crumbs.push({ label: "Analysis", href: "/dashboard/conflicts" });
      crumbs.push({ label: "Implementation Analysis" });
    } else if (pathname === "/dashboard/conflicts") {
      crumbs.push({ label: "Analysis" });
    } else if (pathname === "/browse") {
      crumbs.push({ label: "Browse" });
    } else if (pathname.startsWith("/section/")) {
      crumbs.push({ label: "Search", href: "/search" });
      crumbs.push({ label: "Section Detail" });
    }

    return crumbs;
  };

  const displayBreadcrumbs = breadcrumbs || defaultBreadcrumbs();

  // Determine if secondary nav should be shown
  const isAnalysisSection =
    pathname === "/dashboard/conflicts" ||
    pathname === "/reporting" ||
    pathname === "/anachronisms" ||
    pathname === "/pahlka-implementations";

  return (
    <>
      {/* Primary Navigation Header */}
      <nav className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Logo/Brand */}
            <Link
              href="/"
              className="text-xl font-bold text-slate-900 hover:text-teal-700 transition-colors"
            >
              Deproceduralizer
            </Link>

            {/* Primary Nav Links */}
            <div className="flex gap-6">
              <Link
                href="/search"
                className={`font-medium transition-colors ${
                  pathname === "/search"
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Search
              </Link>
              <Link
                href="/browse"
                className={`font-medium transition-colors ${
                  pathname === "/browse"
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Browse
              </Link>
              <Link
                href="/dashboard/conflicts"
                className={`font-medium transition-colors ${
                  isAnalysisSection
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Analysis
              </Link>
              <Link
                href="/bookmarks"
                className={`font-medium transition-colors ${
                  pathname === "/bookmarks"
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Bookmarks
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Secondary Navigation - Analysis Section */}
      {isAnalysisSection && (
        <div className="bg-slate-50 border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex items-center gap-6 text-sm">
              <Link
                href="/dashboard/conflicts"
                className={`font-medium transition-colors ${
                  pathname === "/dashboard/conflicts"
                    ? "text-teal-700 border-b-2 border-teal-700 pb-1"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Conflicts
              </Link>
              <Link
                href="/reporting"
                className={`font-medium transition-colors ${
                  pathname === "/reporting"
                    ? "text-teal-700 border-b-2 border-teal-700 pb-1"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Reporting
              </Link>
              <Link
                href="/anachronisms"
                className={`font-medium transition-colors ${
                  pathname === "/anachronisms"
                    ? "text-teal-700 border-b-2 border-teal-700 pb-1"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Anachronisms
              </Link>
              <Link
                href="/pahlka-implementations"
                className={`font-medium transition-colors ${
                  pathname === "/pahlka-implementations"
                    ? "text-teal-700 border-b-2 border-teal-700 pb-1"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Implementation
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumbs - Only show when not in analysis section (secondary nav replaces it) */}
      {!isAnalysisSection && displayBreadcrumbs.length > 0 && (
        <div className="bg-slate-50 border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex items-center gap-2 text-sm">
              {displayBreadcrumbs.map((crumb, index) => (
                <div key={index} className="flex items-center gap-2">
                  {index > 0 && (
                    <span className="text-slate-400">›</span>
                  )}
                  {crumb.href ? (
                    <Link
                      href={crumb.href}
                      className="text-slate-600 hover:text-slate-900 transition-colors"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-slate-900 font-medium">
                      {crumb.label}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
