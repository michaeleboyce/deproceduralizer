import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sql } from "drizzle-orm";

/**
 * GET /api/filters/implementations
 *
 * Returns list of unique implementation complexity levels that have results
 * matching the provided filters
 *
 * Query params:
 * - jurisdiction: string (default: "dc")
 * - title: string (optional) - filter by title
 * - chapter: string (optional) - filter by chapter
 * - hasReporting: boolean (optional) - filter by reporting requirement
 * - query: string (optional) - full-text search query
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const jurisdiction = searchParams.get("jurisdiction") || "dc";
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const hasReporting = searchParams.get("hasReporting") === "true";
    const query = searchParams.get("query");

    // Build SQL query that only returns complexity levels with actual results
    const complexityQuery = sql`
      SELECT DISTINCT pi.overall_complexity
      FROM section_pahlka_implementations pi
      INNER JOIN sections s ON (
        s.jurisdiction = pi.jurisdiction
        AND s.id = pi.section_id
      )
      WHERE pi.jurisdiction = ${jurisdiction}
      AND pi.has_implementation_issues = true
      AND pi.overall_complexity IS NOT NULL
      ${title && title.trim() ? sql`AND s.title_label = ${title}` : sql``}
      ${chapter && chapter.trim() ? sql`AND s.chapter_label = ${chapter}` : sql``}
      ${hasReporting ? sql`AND s.has_reporting = true` : sql``}
      ${query && query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${query})` : sql``}
      ORDER BY pi.overall_complexity
    `;

    const result = await db.execute(complexityQuery);
    const complexityLevels = result.rows.map((row: any) => row.overall_complexity).filter(Boolean);

    return NextResponse.json({ complexityLevels });
  } catch (error) {
    console.error("Failed to fetch implementation complexity levels:", error);
    return NextResponse.json(
      { error: "Failed to fetch implementation complexity levels" },
      { status: 500 }
    );
  }
}
