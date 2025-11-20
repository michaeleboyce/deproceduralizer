import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { obligations, sections } from "@/db/schema";
import { sql } from "drizzle-orm";

/**
 * GET /api/filters/obligations
 *
 * Returns list of unique obligation categories that have results
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

    // Build SQL query that only returns categories with actual results
    const categoriesQuery = sql`
      SELECT DISTINCT obl.category
      FROM obligations obl
      INNER JOIN sections s ON (
        s.jurisdiction = obl.jurisdiction
        AND s.id = obl.section_id
      )
      WHERE obl.jurisdiction = ${jurisdiction}
      ${title && title.trim() ? sql`AND s.title_label = ${title}` : sql``}
      ${chapter && chapter.trim() ? sql`AND s.chapter_label = ${chapter}` : sql``}
      ${hasReporting ? sql`AND s.has_reporting = true` : sql``}
      ${query && query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${query})` : sql``}
      ORDER BY obl.category
    `;

    const result = await db.execute(categoriesQuery);
    const categories = result.rows.map((row: any) => row.category);

    return NextResponse.json({ categories });
  } catch (error) {
    console.error("Failed to fetch obligation categories:", error);
    return NextResponse.json(
      { error: "Failed to fetch obligation categories" },
      { status: 500 }
    );
  }
}
