import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sql } from "drizzle-orm";
import { getCurrentJurisdiction } from "@/lib/config";

/**
 * Pahlka Implementation Analysis API endpoint
 *
 * GET /api/pahlka-implementations?complexity=HIGH&category=administrative_burdens&title=Title+1&requiresTechnicalReview=true
 *
 * Returns all sections with implementation issues, with optional filters and sorting
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const complexity = searchParams.get("complexity");
    const category = searchParams.get("category");
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const requiresTechnicalReview = searchParams.get("requiresTechnicalReview");
    const searchQuery = searchParams.get("searchQuery");
    const sortBy = searchParams.get("sortBy") || "complexity"; // complexity | citation | heading

    const jurisdiction = getCurrentJurisdiction();

    // Build WHERE conditions dynamically
    const whereConditions: any[] = [];
    whereConditions.push(sql`pi.jurisdiction = ${jurisdiction}`);
    whereConditions.push(sql`pi.has_implementation_issues = true`);

    if (complexity && complexity.trim()) {
      whereConditions.push(sql`pi.overall_complexity = ${complexity}`);
    }

    if (requiresTechnicalReview === "true") {
      whereConditions.push(sql`pi.requires_technical_review = true`);
    }

    if (title && title.trim()) {
      whereConditions.push(sql`s.title_label = ${title}`);
    }

    if (chapter && chapter.trim()) {
      whereConditions.push(sql`s.chapter_label = ${chapter}`);
    }

    if (searchQuery && searchQuery.trim()) {
      whereConditions.push(
        sql`(pi.summary ILIKE ${'%' + searchQuery + '%'} OR s.heading ILIKE ${'%' + searchQuery + '%'})`
      );
    }

    // Build category filter - need to ensure section has at least one indicator in this category
    if (category && category.trim()) {
      whereConditions.push(
        sql`EXISTS (
          SELECT 1 FROM pahlka_implementation_indicators pii
          WHERE pii.jurisdiction = pi.jurisdiction
          AND pii.section_id = pi.section_id
          AND pii.category = ${category}
        )`
      );
    }

    // Build WHERE clause
    const whereClause = whereConditions.length > 0
      ? sql`WHERE ${sql.join(whereConditions, sql` AND `)}`
      : sql`WHERE true`;

    // Build ORDER BY clause with complexity priority
    const orderByClause =
      sortBy === "citation"
        ? sql`ORDER BY s.citation`
        : sortBy === "heading"
        ? sql`ORDER BY s.heading`
        : sql`ORDER BY
            CASE pi.overall_complexity
              WHEN 'HIGH' THEN 1
              WHEN 'MEDIUM' THEN 2
              WHEN 'LOW' THEN 3
              ELSE 4
            END,
            pi.requires_technical_review DESC,
            s.citation`;

    // Main query to get sections with their implementation analysis details
    const mainSql = sql`
      WITH indicators_agg AS (
        SELECT
          pii.jurisdiction,
          pii.section_id,
          json_agg(
            json_build_object(
              'id', pii.id,
              'category', pii.category,
              'complexity', pii.complexity,
              'implementationApproach', pii.implementation_approach,
              'effortEstimate', pii.effort_estimate,
              'explanation', pii.explanation,
              'matchedPhrases', (
                SELECT json_agg(h.phrase)
                FROM section_pahlka_highlights h
                WHERE h.indicator_id = pii.id
              )
            ) ORDER BY
              CASE pii.complexity
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
              END
          ) as indicators
        FROM pahlka_implementation_indicators pii
        WHERE pii.jurisdiction = ${jurisdiction}
        GROUP BY pii.jurisdiction, pii.section_id
      )
      SELECT
        pi.section_id as id,
        s.citation,
        s.heading,
        s.title_label,
        s.chapter_label,
        pi.has_implementation_issues,
        pi.overall_complexity,
        pi.summary,
        pi.requires_technical_review,
        pi.model_used,
        pi.analyzed_at,
        COALESCE(ind.indicators, '[]'::json) as indicators
      FROM section_pahlka_implementations pi
      INNER JOIN sections s ON s.jurisdiction = pi.jurisdiction AND s.id = pi.section_id
      LEFT JOIN indicators_agg ind ON ind.jurisdiction = pi.jurisdiction AND ind.section_id = pi.section_id
      ${whereClause}
      ${orderByClause}
    `;

    const results = await db.execute(mainSql);

    // Get total count
    const countSql = sql`
      SELECT COUNT(DISTINCT pi.section_id)::int as count
      FROM section_pahlka_implementations pi
      INNER JOIN sections s ON s.jurisdiction = pi.jurisdiction AND s.id = pi.section_id
      ${whereClause}
    `;

    const countResult = await db.execute(countSql);
    const total = (countResult.rows[0] as any)?.count || 0;

    // Get all unique categories for the filter dropdown
    const allCategoriesSql = sql`
      SELECT DISTINCT pii.category, COUNT(*)::int as count
      FROM pahlka_implementation_indicators pii
      INNER JOIN section_pahlka_implementations pi ON pi.jurisdiction = pii.jurisdiction AND pi.section_id = pii.section_id
      WHERE pii.jurisdiction = ${jurisdiction} AND pi.has_implementation_issues = true
      GROUP BY pii.category
      ORDER BY pii.category
    `;

    const allCategoriesResult = await db.execute(allCategoriesSql);
    const allCategories = allCategoriesResult.rows;

    // Get complexity distribution
    const complexityDistributionSql = sql`
      SELECT
        overall_complexity as complexity,
        COUNT(*)::int as count
      FROM section_pahlka_implementations
      WHERE jurisdiction = ${jurisdiction} AND has_implementation_issues = true
      GROUP BY overall_complexity
      ORDER BY
        CASE overall_complexity
          WHEN 'HIGH' THEN 1
          WHEN 'MEDIUM' THEN 2
          WHEN 'LOW' THEN 3
        END
    `;

    const complexityDistributionResult = await db.execute(complexityDistributionSql);
    const complexityDistribution = complexityDistributionResult.rows;

    // Get technical review stats
    const technicalReviewStatsSql = sql`
      SELECT
        COUNT(*) FILTER (WHERE requires_technical_review = true)::int as requires_review,
        COUNT(*)::int as total
      FROM section_pahlka_implementations
      WHERE jurisdiction = ${jurisdiction} AND has_implementation_issues = true
    `;

    const technicalReviewStatsResult = await db.execute(technicalReviewStatsSql);
    const technicalReviewStats = technicalReviewStatsResult.rows[0];

    return NextResponse.json({
      results: results.rows,
      total,
      filters: {
        complexity: complexity || null,
        category: category || null,
        title: title || null,
        chapter: chapter || null,
        requiresTechnicalReview: requiresTechnicalReview === "true" ? true : null,
        searchQuery: searchQuery || null,
        sortBy,
      },
      allCategories,
      complexityDistribution,
      technicalReviewStats,
    });
  } catch (error) {
    console.error("Pahlka Implementation API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch implementation analysis", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
