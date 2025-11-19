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
    } else if (pathname === "/reporting") {
      crumbs.push({ label: "Reporting Requirements" });
    } else if (pathname === "/browse") {
      crumbs.push({ label: "Browse" });
    } else if (pathname.startsWith("/section/")) {
      crumbs.push({ label: "Search", href: "/search" });
      crumbs.push({ label: "Section Detail" });
    }

    return crumbs;
  };

  const displayBreadcrumbs = breadcrumbs || defaultBreadcrumbs();

  return (
    <>
      {/* Main Navigation Header */}
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

            {/* Nav Links */}
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
                href="/reporting"
                className={`font-medium transition-colors ${
                  pathname === "/reporting"
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Reporting
              </Link>
              <Link
                href="/dashboard/conflicts"
                className={`font-medium transition-colors ${
                  pathname === "/dashboard/conflicts"
                    ? "text-teal-700"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                Analysis
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Breadcrumbs */}
      {displayBreadcrumbs.length > 0 && (
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
