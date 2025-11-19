import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sql } from "drizzle-orm";

/**
 * Anachronisms API endpoint
 *
 * GET /api/anachronisms?severity=CRITICAL&category=jim_crow&title=Title+1&requiresReview=true
 *
 * Returns all sections with anachronisms, with optional filters and sorting
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const severity = searchParams.get("severity");
    const category = searchParams.get("category");
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const requiresReview = searchParams.get("requiresReview");
    const searchQuery = searchParams.get("searchQuery");
    const sortBy = searchParams.get("sortBy") || "severity"; // severity | citation | heading

    // Hardcode jurisdiction to 'dc' for now
    const jurisdiction = 'dc';

    // Build WHERE conditions dynamically
    const whereConditions: any[] = [];
    whereConditions.push(sql`sa.jurisdiction = 'dc'`);
    whereConditions.push(sql`sa.has_anachronism = true`);

    if (severity && severity.trim()) {
      whereConditions.push(sql`sa.overall_severity = ${severity}`);
    }

    if (requiresReview === "true") {
      whereConditions.push(sql`sa.requires_immediate_review = true`);
    }

    if (title && title.trim()) {
      whereConditions.push(sql`s.title_label = ${title}`);
    }

    if (chapter && chapter.trim()) {
      whereConditions.push(sql`s.chapter_label = ${chapter}`);
    }

    if (searchQuery && searchQuery.trim()) {
      whereConditions.push(
        sql`(sa.summary ILIKE ${'%' + searchQuery + '%'} OR s.heading ILIKE ${'%' + searchQuery + '%'})`
      );
    }

    // If category filter is specified, join with indicators
    const categoryJoinClause = category && category.trim()
      ? sql`INNER JOIN anachronism_indicators ai ON ai.jurisdiction = 'dc' AND ai.section_id = sa.section_id AND ai.category = ${category}`
      : sql``;

    // Build WHERE clause
    const whereClause = whereConditions.length > 0
      ? sql`WHERE ${sql.join(whereConditions, sql` AND `)}`
      : sql`WHERE true`;

    // Build ORDER BY clause with severity priority
    const orderByClause =
      sortBy === "citation"
        ? sql`ORDER BY s.citation`
        : sortBy === "heading"
        ? sql`ORDER BY s.heading`
        : sql`ORDER BY
            CASE sa.overall_severity
              WHEN 'CRITICAL' THEN 1
              WHEN 'HIGH' THEN 2
              WHEN 'MEDIUM' THEN 3
              WHEN 'LOW' THEN 4
              ELSE 5
            END,
            sa.requires_immediate_review DESC,
            s.citation`;

    // Main query to get sections with their anachronism details
    const mainSql = sql`
      WITH indicators_agg AS (
        SELECT
          ai.jurisdiction,
          ai.section_id,
          json_agg(
            json_build_object(
              'id', ai.id,
              'category', ai.category,
              'severity', ai.severity,
              'modernEquivalent', ai.modern_equivalent,
              'recommendation', ai.recommendation,
              'explanation', ai.explanation,
              'matchedPhrases', (
                SELECT json_agg(h.phrase)
                FROM section_anachronism_highlights h
                WHERE h.indicator_id = ai.id
              )
            ) ORDER BY
              CASE ai.severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
              END
          ) as indicators
        FROM anachronism_indicators ai
        WHERE ai.jurisdiction = 'dc'
        GROUP BY ai.jurisdiction, ai.section_id
      )
      SELECT
        sa.section_id as id,
        s.citation,
        s.heading,
        s.title_label,
        s.chapter_label,
        sa.has_anachronism,
        sa.overall_severity,
        sa.summary,
        sa.requires_immediate_review,
        sa.model_used,
        sa.analyzed_at,
        COALESCE(ind.indicators, '[]'::json) as indicators
      FROM section_anachronisms sa
      INNER JOIN sections s ON s.jurisdiction = sa.jurisdiction AND s.id = sa.section_id
      ${categoryJoinClause}
      LEFT JOIN indicators_agg ind ON ind.jurisdiction = sa.jurisdiction AND ind.section_id = sa.section_id
      ${whereClause}
      ${orderByClause}
    `;

    const results = await db.execute(mainSql);

    // Get total count
    const countSql = sql`
      SELECT COUNT(DISTINCT sa.section_id)::int as count
      FROM section_anachronisms sa
      INNER JOIN sections s ON s.jurisdiction = sa.jurisdiction AND s.id = sa.section_id
      ${categoryJoinClause}
      ${whereClause}
    `;

    const countResult = await db.execute(countSql);
    const total = (countResult.rows[0] as any)?.count || 0;

    // Get all unique categories for the filter dropdown
    const allCategoriesSql = sql`
      SELECT DISTINCT ai.category, COUNT(*)::int as count
      FROM anachronism_indicators ai
      INNER JOIN section_anachronisms sa ON sa.jurisdiction = ai.jurisdiction AND sa.section_id = ai.section_id
      WHERE ai.jurisdiction = 'dc' AND sa.has_anachronism = true
      GROUP BY ai.category
      ORDER BY ai.category
    `;

    const allCategoriesResult = await db.execute(allCategoriesSql);
    const allCategories = allCategoriesResult.rows;

    // Get severity distribution
    const severityDistributionSql = sql`
      SELECT
        overall_severity as severity,
        COUNT(*)::int as count
      FROM section_anachronisms
      WHERE jurisdiction = 'dc' AND has_anachronism = true
      GROUP BY overall_severity
      ORDER BY
        CASE overall_severity
          WHEN 'CRITICAL' THEN 1
          WHEN 'HIGH' THEN 2
          WHEN 'MEDIUM' THEN 3
          WHEN 'LOW' THEN 4
        END
    `;

    const severityDistributionResult = await db.execute(severityDistributionSql);
    const severityDistribution = severityDistributionResult.rows;

    return NextResponse.json({
      results: results.rows,
      total,
      filters: {
        severity: severity || null,
        category: category || null,
        title: title || null,
        chapter: chapter || null,
        requiresReview: requiresReview === "true" ? true : null,
        searchQuery: searchQuery || null,
        sortBy,
      },
      allCategories,
      severityDistribution,
    });
  } catch (error) {
    console.error("Anachronisms API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch anachronisms", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
