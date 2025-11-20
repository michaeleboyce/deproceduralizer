import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sql } from "drizzle-orm";

/**
 * GET /api/filters/anachronisms
 *
 * Returns list of unique anachronism severity levels that have results
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

    // Build SQL query that only returns severity levels with actual results
    const severityQuery = sql`
      SELECT DISTINCT sa.overall_severity
      FROM section_anachronisms sa
      INNER JOIN sections s ON (
        s.jurisdiction = sa.jurisdiction
        AND s.id = sa.section_id
      )
      WHERE sa.jurisdiction = ${jurisdiction}
      AND sa.has_anachronism = true
      AND sa.overall_severity IS NOT NULL
      ${title && title.trim() ? sql`AND s.title_label = ${title}` : sql``}
      ${chapter && chapter.trim() ? sql`AND s.chapter_label = ${chapter}` : sql``}
      ${hasReporting ? sql`AND s.has_reporting = true` : sql``}
      ${query && query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${query})` : sql``}
      ORDER BY sa.overall_severity
    `;

    const result = await db.execute(severityQuery);
    const severityLevels = result.rows.map((row: any) => row.overall_severity).filter(Boolean);

    return NextResponse.json({ severityLevels });
  } catch (error) {
    console.error("Failed to fetch anachronism severity levels:", error);
    return NextResponse.json(
      { error: "Failed to fetch anachronism severity levels" },
      { status: 500 }
    );
  }
}
