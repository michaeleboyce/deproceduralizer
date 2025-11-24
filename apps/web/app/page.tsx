import Link from "next/link";
import { db } from "@/lib/db";
import { sql } from "drizzle-orm";
import { AlertTriangle, Clock, Settings, Calendar } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import Navigation from "@/components/Navigation";
import { getCurrentJurisdiction } from "@/lib/config";

async function getAnalysisStats() {
  const jurisdiction = getCurrentJurisdiction();

  try {
    // Get conflict counts
    const conflictsResult = await db.execute(sql`
      SELECT classification, COUNT(*) as count
      FROM section_similarity_classifications
      WHERE jurisdiction = ${jurisdiction}
      GROUP BY classification
    `);

    const conflicts = conflictsResult.rows.reduce((acc: any, row: any) => {
      acc[row.classification] = parseInt(row.count);
      return acc;
    }, {});

    // Get anachronism counts
    const anachronismsResult = await db.execute(sql`
      SELECT
        COUNT(*) FILTER (WHERE has_anachronism = true) as total,
        COUNT(*) FILTER (WHERE requires_immediate_review = true) as immediate,
        COUNT(*) FILTER (WHERE overall_severity = 'CRITICAL') as critical,
        COUNT(*) FILTER (WHERE overall_severity = 'HIGH') as high
      FROM section_anachronisms
      WHERE jurisdiction = ${jurisdiction}
    `);

    const anachronisms = anachronismsResult.rows[0] as any;

    // Get Pahlka implementation counts
    const pahlkaResult = await db.execute(sql`
      SELECT
        COUNT(*) FILTER (WHERE has_implementation_issues = true) as total,
        COUNT(*) FILTER (WHERE requires_technical_review = true) as technical_review,
        COUNT(*) FILTER (WHERE overall_complexity = 'HIGH') as high_complexity
      FROM section_pahlka_implementations
      WHERE jurisdiction = ${jurisdiction}
    `);

    const pahlka = pahlkaResult.rows[0] as any;

    // Get reporting requirements count
    const reportingResult = await db.execute(sql`
      SELECT COUNT(*) as count
      FROM sections
      WHERE jurisdiction = ${jurisdiction} AND has_reporting = true
    `);

    const reporting = parseInt((reportingResult.rows[0] as any)?.count || '0');

    // Get total sections count
    const sectionsResult = await db.execute(sql`
      SELECT COUNT(*) as count
      FROM sections
      WHERE jurisdiction = ${jurisdiction}
    `);

    const totalSections = parseInt((sectionsResult.rows[0] as any)?.count || '0');

    return {
      conflicts: {
        conflicting: conflicts.conflicting || 0,
        duplicate: conflicts.duplicate || 0,
      },
      anachronisms: {
        total: parseInt(anachronisms.total || '0'),
        immediate: parseInt(anachronisms.immediate || '0'),
        critical: parseInt(anachronisms.critical || '0'),
        high: parseInt(anachronisms.high || '0'),
      },
      pahlka: {
        total: parseInt(pahlka.total || '0'),
        technicalReview: parseInt(pahlka.technical_review || '0'),
        highComplexity: parseInt(pahlka.high_complexity || '0'),
      },
      reporting,
      totalSections,
    };
  } catch (error) {
    console.error("Error fetching analysis stats:", error);
    return {
      conflicts: { conflicting: 0, duplicate: 0 },
      anachronisms: { total: 0, immediate: 0, critical: 0, high: 0 },
      pahlka: { total: 0, technicalReview: 0, highComplexity: 0 },
      reporting: 0,
      totalSections: 0,
    };
  }
}

export default async function HomePage() {
  const stats = await getAnalysisStats();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-teal-50/30">
      <Navigation />

      {/* Hero Section */}
      <div className="max-w-6xl mx-auto px-4 py-20 md:py-32">
        <div className="text-center mb-12">
          <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold text-slate-900 mb-6 tracking-tight leading-none">
            Deproceduralizer
          </h1>
          <p className="text-2xl md:text-3xl text-slate-600 mb-4 font-light">
            Search and analyze Washington, D.C. legal code
          </p>
          <p className="text-base text-slate-500">
            Full-text search • Cross-references • Obligations tracking
          </p>
        </div>

        {/* Enhanced Search Bar */}
        <div className="max-w-4xl mx-auto mb-24">
          <SearchBar />
        </div>

        {/* Analysis Features Grid */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-2 text-center">
            AI-Powered Legal Analysis
          </h2>
          <p className="text-slate-600 text-center mb-8">
            Sophisticated analysis tools to identify issues and improve legal code quality
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-16">
          {/* Legislative Conflicts */}
          <Link
            href="/dashboard/conflicts"
            className="group bg-white p-8 rounded-xl border-2 border-red-100 shadow-sm hover:shadow-lg hover:border-red-200 transition-all"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-red-50 rounded-lg group-hover:bg-red-100 transition-colors">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1 text-xl group-hover:text-red-700 transition-colors">
                  Legislative Conflicts
                </h3>
                <p className="text-sm text-slate-600">
                  Identify contradictions and duplicates in legal code
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-100">
              <div>
                <div className="text-3xl font-bold text-red-600 mb-1">
                  {stats.conflicts.conflicting}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  Conflicting
                </div>
              </div>
              <div>
                <div className="text-3xl font-bold text-amber-600 mb-1">
                  {stats.conflicts.duplicate}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  Duplicates
                </div>
              </div>
            </div>
          </Link>

          {/* Anachronistic Language */}
          <Link
            href="/anachronisms"
            className="group bg-white p-8 rounded-xl border-2 border-orange-100 shadow-sm hover:shadow-lg hover:border-orange-200 transition-all"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-orange-50 rounded-lg group-hover:bg-orange-100 transition-colors">
                <Clock className="w-6 h-6 text-orange-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1 text-xl group-hover:text-orange-700 transition-colors">
                  Anachronistic Language
                </h3>
                <p className="text-sm text-slate-600">
                  Detect outdated references and obsolete provisions
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-100">
              <div>
                <div className="text-3xl font-bold text-orange-600 mb-1">
                  {stats.anachronisms.total}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  Flagged
                </div>
              </div>
              <div>
                <div className="text-3xl font-bold text-red-600 mb-1">
                  {stats.anachronisms.immediate}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  Urgent
                </div>
              </div>
            </div>
          </Link>

          {/* Implementation Analysis */}
          <Link
            href="/pahlka-implementations"
            className="group bg-white p-8 rounded-xl border-2 border-purple-100 shadow-sm hover:shadow-lg hover:border-purple-200 transition-all"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-purple-50 rounded-lg group-hover:bg-purple-100 transition-colors">
                <Settings className="w-6 h-6 text-purple-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1 text-xl group-hover:text-purple-700 transition-colors">
                  Implementation Analysis
                </h3>
                <p className="text-sm text-slate-600">
                  Pahlka framework: identify complexity and burden
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-100">
              <div>
                <div className="text-3xl font-bold text-purple-600 mb-1">
                  {stats.pahlka.total}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  Issues Found
                </div>
              </div>
              <div>
                <div className="text-3xl font-bold text-purple-700 mb-1">
                  {stats.pahlka.highComplexity}
                </div>
                <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                  High Complexity
                </div>
              </div>
            </div>
          </Link>

          {/* Reporting Requirements */}
          <Link
            href="/reporting"
            className="group bg-white p-8 rounded-xl border-2 border-teal-100 shadow-sm hover:shadow-lg hover:border-teal-200 transition-all"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="p-3 bg-teal-50 rounded-lg group-hover:bg-teal-100 transition-colors">
                <Calendar className="w-6 h-6 text-teal-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 mb-1 text-xl group-hover:text-teal-700 transition-colors">
                  Reporting Requirements
                </h3>
                <p className="text-sm text-slate-600">
                  Track obligations, deadlines, and compliance
                </p>
              </div>
            </div>
            <div className="pt-4 border-t border-slate-100">
              <div className="text-3xl font-bold text-teal-600 mb-1">
                {stats.reporting}
              </div>
              <div className="text-xs text-slate-600 font-medium uppercase tracking-wide">
                Obligations Tracked
              </div>
            </div>
          </Link>
        </div>

        {/* Stats */}
        <div className="bg-gradient-to-br from-slate-50/50 to-white rounded-xl border border-slate-200 shadow-sm p-10 mb-16">
          <h3 className="text-xl font-semibold text-slate-900 mb-8 text-center">
            Current Database
          </h3>
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">
                {stats.totalSections.toLocaleString()}
              </div>
              <div className="text-sm text-slate-600 font-medium">Sections</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">10</div>
              <div className="text-sm text-slate-600 font-medium">Titles</div>
            </div>
            <div>
              <div className="text-5xl font-bold text-teal-700 mb-2">100%</div>
              <div className="text-sm text-slate-600 font-medium">FTS Indexed</div>
            </div>
          </div>
          <p className="text-xs text-slate-500 text-center mt-8 px-4">
            Currently loaded: DC Code Titles 1-10 (medium dataset for development)
          </p>
        </div>

        {/* About */}
        <div className="text-center">
          <p className="text-slate-600 max-w-2xl mx-auto leading-relaxed text-lg">
            The Deproceduralizer makes DC legal code more accessible through
            modern search technology, semantic analysis, and automated
            extraction of key obligations and requirements.
          </p>
        </div>
      </div>
    </div>
  );
}
