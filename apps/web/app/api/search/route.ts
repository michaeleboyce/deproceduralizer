import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { dcSections, dcSectionSimilarities, dcSectionSimilarityClassifications } from "@/db/schema";
import { sql, and, eq, SQL, gte, lte, or } from "drizzle-orm";

/**
 * Search API endpoint
 *
 * GET /api/search?query=term&title=Title+1&chapter=Chapter+1&page=1&limit=20
 *   &hasSimilar=true&minSimilarity=0.8&maxSimilarity=1.0&similarityClassification=duplicate
 *
 * Searches DC Code sections using PostgreSQL full-text search with filters
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get("query");
    const title = searchParams.get("title");
    const chapter = searchParams.get("chapter");
    const hasReporting = searchParams.get("hasReporting") === "true";
    const hasSimilar = searchParams.get("hasSimilar") === "true";
    const minSimilarity = parseFloat(searchParams.get("minSimilarity") || "0.7");
    const maxSimilarity = parseFloat(searchParams.get("maxSimilarity") || "1.0");
    const similarityClassification = searchParams.get("similarityClassification");
    const page = parseInt(searchParams.get("page") || "1", 10);
    const limit = parseInt(searchParams.get("limit") || "20", 10);

    // Calculate offset for pagination
    const offset = (page - 1) * limit;

    // Check if we need similarity filtering
    const needsSimilarityJoin = hasSimilar || minSimilarity > 0.7 || maxSimilarity < 1.0 || similarityClassification;

    if (needsSimilarityJoin) {
      // Complex query with similarity joins
      const baseSql = sql`
        SELECT DISTINCT
          s.id,
          s.citation,
          s.heading,
          LEFT(s.text_plain, 200) as snippet,
          s.title_label,
          s.chapter_label
        FROM dc_sections s
        INNER JOIN dc_section_similarities sim ON (
          (sim.section_a = s.id OR sim.section_b = s.id)
          ${minSimilarity > 0.7 ? sql`AND sim.similarity >= ${minSimilarity}` : sql``}
          ${maxSimilarity < 1.0 ? sql`AND sim.similarity <= ${maxSimilarity}` : sql``}
        )
        ${similarityClassification ? sql`
          INNER JOIN dc_section_similarity_classifications cls ON (
            cls.section_a = sim.section_a AND cls.section_b = sim.section_b
            AND cls.classification = ${similarityClassification}
          )
        ` : sql``}
        WHERE 1=1
        ${query && query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${query})` : sql``}
        ${title && title.trim() ? sql`AND s.title_label = ${title}` : sql``}
        ${chapter && chapter.trim() ? sql`AND s.chapter_label = ${chapter}` : sql``}
        ${hasReporting ? sql`AND s.has_reporting = true` : sql``}
        ORDER BY s.citation
        LIMIT ${limit}
        OFFSET ${offset}
      `;

      const countSql = sql`
        SELECT COUNT(DISTINCT s.id)::int as count
        FROM dc_sections s
        INNER JOIN dc_section_similarities sim ON (
          (sim.section_a = s.id OR sim.section_b = s.id)
          ${minSimilarity > 0.7 ? sql`AND sim.similarity >= ${minSimilarity}` : sql``}
          ${maxSimilarity < 1.0 ? sql`AND sim.similarity <= ${maxSimilarity}` : sql``}
        )
        ${similarityClassification ? sql`
          INNER JOIN dc_section_similarity_classifications cls ON (
            cls.section_a = sim.section_a AND cls.section_b = sim.section_b
            AND cls.classification = ${similarityClassification}
          )
        ` : sql``}
        WHERE 1=1
        ${query && query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${query})` : sql``}
        ${title && title.trim() ? sql`AND s.title_label = ${title}` : sql``}
        ${chapter && chapter.trim() ? sql`AND s.chapter_label = ${chapter}` : sql``}
        ${hasReporting ? sql`AND s.has_reporting = true` : sql``}
      `;

      const results = await db.execute(baseSql);
      const countResultData = await db.execute(countSql);
      const countRow = countResultData.rows[0] as { count: number } | undefined;
      const total = countRow?.count || 0;
      const totalPages = Math.ceil(total / limit);

      return NextResponse.json({
        results: results.rows,
        query: query || "",
        count: results.rows.length,
        total,
        page,
        limit,
        totalPages,
        filters: {
          title: title || null,
          chapter: chapter || null,
          hasReporting: hasReporting,
          hasSimilar: hasSimilar,
          minSimilarity: minSimilarity,
          maxSimilarity: maxSimilarity,
          similarityClassification: similarityClassification || null,
        },
      });
    } else {
      // Simple query without similarity joins
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

      // Add reporting filter if provided
      if (hasReporting) {
        conditions.push(eq(dcSections.hasReporting, true));
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
          hasReporting: hasReporting,
          hasSimilar: false,
          minSimilarity: 0.7,
          maxSimilarity: 1.0,
          similarityClassification: null,
        },
      });
    }
  } catch (error) {
    console.error("Search error:", error);
    return NextResponse.json(
      { error: "Failed to search sections" },
      { status: 500 }
    );
  }
}
