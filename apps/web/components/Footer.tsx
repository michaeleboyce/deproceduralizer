import Link from "next/link";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-900 text-slate-300 mt-20">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
          {/* About Column */}
          <div>
            <h3 className="text-white font-semibold text-lg mb-4">
              Deproceduralizer
            </h3>
            <p className="text-sm text-slate-400 mb-4">
              A modern tool for searching and analyzing Washington, D.C. legal code with
              advanced semantic analysis and cross-referencing capabilities.
            </p>
            <p className="text-xs text-slate-500">
              Version 0.1.0
            </p>
          </div>

          {/* Navigation Column */}
          <div>
            <h4 className="text-white font-semibold mb-4">Navigate</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  href="/search"
                  className="hover:text-teal-400 transition-colors"
                >
                  Search
                </Link>
              </li>
              <li>
                <Link
                  href="/browse"
                  className="hover:text-teal-400 transition-colors"
                >
                  Browse Code
                </Link>
              </li>
              <li>
                <Link
                  href="/reporting"
                  className="hover:text-teal-400 transition-colors"
                >
                  Reporting Requirements
                </Link>
              </li>
              <li>
                <Link
                  href="/anachronisms"
                  className="hover:text-teal-400 transition-colors"
                >
                  Anachronisms
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/conflicts"
                  className="hover:text-teal-400 transition-colors"
                >
                  Legislative Analysis
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources Column */}
          <div>
            <h4 className="text-white font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="https://github.com/DCCouncil/law-xml"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-teal-400 transition-colors inline-flex items-center gap-1"
                >
                  DC Law XML
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/anthropics/claude-code"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-teal-400 transition-colors inline-flex items-center gap-1"
                >
                  Built with Claude Code
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </li>
              <li>
                <Link
                  href="/pahlka-implementations"
                  className="hover:text-teal-400 transition-colors"
                >
                  Implementation Analysis
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal/Info Column */}
          <div>
            <h4 className="text-white font-semibold mb-4">Information</h4>
            <ul className="space-y-2 text-sm">
              <li className="text-slate-400">
                Data sourced from the official DC Code XML repository
              </li>
              <li className="text-slate-400">
                Analysis powered by semantic search and LLM classification
              </li>
              <li className="text-xs text-slate-500 mt-4">
                This tool is for research and educational purposes. Always verify legal information with official sources.
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-sm text-slate-500">
            © {currentYear} Deproceduralizer. All rights reserved.
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <span>
              Powered by{" "}
              <a
                href="https://nextjs.org"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-teal-400 transition-colors"
              >
                Next.js
              </a>
              {" "}+{" "}
              <a
                href="https://www.postgresql.org"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-teal-400 transition-colors"
              >
                PostgreSQL
              </a>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
