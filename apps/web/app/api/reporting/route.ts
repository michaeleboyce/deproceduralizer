import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sections, sectionTags, globalTags } from "@/db/schema";
import { sql, and, eq, SQL, or, like } from "drizzle-orm";

/**
 * Reporting Requirements API endpoint
 *
 * GET /api/reporting?tag=mayor&title=Title+1&chapter=Chapter+1&searchQuery=annual&sortBy=citation
 *
 * Returns all sections with reporting requirements, with optional filters and sorting
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const tag = searchParams.get("tag");
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const searchQuery = searchParams.get("searchQuery");
    const sortBy = searchParams.get("sortBy") || "citation"; // citation | titleLabel | heading

    // Hardcode jurisdiction to 'dc' for now (transparent to user)
    const jurisdiction = 'dc';

    // Build WHERE conditions dynamically
    const whereConditions: SQL[] = [];
    whereConditions.push(sql`s.jurisdiction = ${jurisdiction}`);
    whereConditions.push(sql`s.has_reporting = true`);

    if (title && title.trim()) {
      whereConditions.push(sql`s.title_label = ${title}`);
    }

    if (chapter && chapter.trim()) {
      whereConditions.push(sql`s.chapter_label = ${chapter}`);
    }

    if (searchQuery && searchQuery.trim()) {
      whereConditions.push(
        sql`(s.reporting_summary ILIKE ${'%' + searchQuery + '%'} OR s.heading ILIKE ${'%' + searchQuery + '%'})`
      );
    }

    // Build tag join clause
    const tagJoinClause = tag && tag.trim()
      ? sql`INNER JOIN section_tags st ON st.jurisdiction = ${jurisdiction} AND st.section_id = s.id AND st.tag = ${tag}`
      : sql``;

    // Build WHERE clause
    const whereClause = whereConditions.length > 0
      ? sql`WHERE ${sql.join(whereConditions, sql` AND `)}`
      : sql`WHERE true`;

    // Build ORDER BY clause
    const orderByClause =
      sortBy === "titleLabel"
        ? sql`ORDER BY s.title_label, s.citation`
        : sortBy === "heading"
        ? sql`ORDER BY s.heading`
        : sql`ORDER BY s.citation`;

    // Main query to get sections with their tags
    const mainSql = sql`
      WITH section_tags_agg AS (
        SELECT
          st.section_id,
          json_agg(st.tag ORDER BY st.tag) as tags
        FROM section_tags st
        WHERE st.jurisdiction = ${jurisdiction}
        GROUP BY st.section_id
      )
      SELECT
        s.id,
        s.citation,
        s.heading,
        s.reporting_summary,
        s.title_label,
        s.chapter_label,
        COALESCE(tags.tags, '[]'::json) as tags
      FROM sections s
      ${tagJoinClause}
      LEFT JOIN section_tags_agg tags ON tags.section_id = s.id
      ${whereClause}
      ${orderByClause}
    `;

    const results = await db.execute(mainSql);

    // Get total count
    const countSql = sql`
      SELECT COUNT(DISTINCT s.id)::int as count
      FROM sections s
      ${tagJoinClause}
      ${whereClause}
    `;

    const countResult = await db.execute(countSql);
    const total = (countResult.rows[0] as any)?.count || 0;

    // Get all unique tags for the filter dropdown
    const allTagsSql = sql`
      SELECT DISTINCT st.tag
      FROM section_tags st
      INNER JOIN sections s ON s.jurisdiction = st.jurisdiction AND s.id = st.section_id
      WHERE st.jurisdiction = ${jurisdiction} AND s.has_reporting = true
      ORDER BY st.tag
    `;

    const allTagsResult = await db.execute(allTagsSql);
    const allTags = allTagsResult.rows.map((row: any) => row.tag);

    return NextResponse.json({
      results: results.rows,
      total,
      filters: {
        tag: tag || null,
        title: title || null,
        chapter: chapter || null,
        searchQuery: searchQuery || null,
        sortBy,
      },
      allTags,
    });
  } catch (error) {
    console.error("Reporting API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch reporting requirements", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
