import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { dcSections } from "@/db/schema";
import { sql, and, eq, SQL } from "drizzle-orm";

/**
 * Search API endpoint
 *
 * GET /api/search?query=term&title=Title+1&chapter=Chapter+1&page=1&limit=20
 *
 * Searches DC Code sections using PostgreSQL full-text search with filters
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get("query");
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const page = parseInt(searchParams.get("page") || "1", 10);
    const limit = parseInt(searchParams.get("limit") || "20", 10);

    // Calculate offset for pagination
    const offset = (page - 1) * limit;

    // Build WHERE conditions
    const conditions: SQL[] = [];

    // Add FTS condition if query provided
    if (query && query.trim()) {
      conditions.push(
        sql`text_fts @@ plainto_tsquery('english', ${query})`
      );
    }

    // Add title filter if provided
    if (title && title.trim()) {
      conditions.push(eq(dcSections.titleLabel, title));
    }

    // Add chapter filter if provided
    if (chapter && chapter.trim()) {
      conditions.push(eq(dcSections.chapterLabel, chapter));
    }

    // Combine all conditions
    const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

    // Get total count for pagination
    const [countResult] = await db
      .select({ count: sql<number>`count(*)::int` })
      .from(dcSections)
      .where(whereClause);

    const total = countResult?.count || 0;
    const totalPages = Math.ceil(total / limit);

    // Get paginated results
    const results = await db
      .select({
        id: dcSections.id,
        citation: dcSections.citation,
        heading: dcSections.heading,
        snippet: sql<string>`LEFT(${dcSections.textPlain}, 200)`,
        titleLabel: dcSections.titleLabel,
        chapterLabel: dcSections.chapterLabel,
      })
      .from(dcSections)
      .where(whereClause)
      .limit(limit)
      .offset(offset)
      .orderBy(dcSections.citation);

    return NextResponse.json({
      results,
      query: query || "",
      count: results.length,
      total,
      page,
      limit,
      totalPages,
      filters: {
        title: title || null,
        chapter: chapter || null,
      },
    });
  } catch (error) {
    console.error("Search error:", error);
    return NextResponse.json(
      { error: "Failed to search sections" },
      { status: 500 }
    );
  }
}
