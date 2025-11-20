import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sections, sectionSimilarities, sectionSimilarityClassifications, obligations } from "@/db/schema";
import { sql, and, eq, SQL, gte, lte, or } from "drizzle-orm";

/**
 * Search API endpoint
 *
 * GET /api/search?query=term&title=Title+1&chapter=Chapter+1&page=1&limit=20
 *   &hasSimilar=true&minSimilarity=0.8&maxSimilarity=1.0&similarityClassification=duplicate
 *   &obligationCategory=deadline,penalty
 *
 * Searches code sections using PostgreSQL full-text search with filters
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
    const obligationCategories = searchParams.get("obligationCategory")?.split(",").filter(Boolean);
    const hasImplementationIssues = searchParams.get("hasImplementationIssues") === "true";
    const implementationComplexity = searchParams.get("implementationComplexity");
    const hasAnachronisms = searchParams.get("hasAnachronisms") === "true";
    const anachronismSeverity = searchParams.get("anachronismSeverity");
    const page = parseInt(searchParams.get("page") || "1", 10);
    const limit = parseInt(searchParams.get("limit") || "20", 10);

    // Hardcode jurisdiction to 'dc' for now (transparent to user)
    const jurisdiction = 'dc';

    // Calculate offset for pagination
    const offset = (page - 1) * limit;

    // Check if we need similarity filtering
    const needsSimilarityJoin = hasSimilar || minSimilarity > 0.7 || maxSimilarity < 1.0 || similarityClassification;

    // Check if we need obligations filtering
    const needsObligationsJoin = obligationCategories && obligationCategories.length > 0;

    // Check if we need implementation filtering
    const needsImplementationJoin = hasImplementationIssues;

    // Check if we need anachronism filtering
    const needsAnachronismJoin = hasAnachronisms;

    if (needsSimilarityJoin || needsObligationsJoin || needsImplementationJoin || needsAnachronismJoin) {
      // Complex query with similarity, obligations, implementation, and/or anachronism joins
      const baseSql = sql`
        SELECT DISTINCT
          s.id,
          s.citation,
          s.heading,
          LEFT(s.text_plain, 200) as snippet,
          s.title_label,
          s.chapter_label
        FROM sections s
        ${needsSimilarityJoin ? sql`
          INNER JOIN section_similarities sim ON (
            sim.jurisdiction = ${jurisdiction}
            AND (sim.section_a = s.id OR sim.section_b = s.id)
            ${minSimilarity > 0.7 ? sql`AND sim.similarity >= ${minSimilarity}` : sql``}
            ${maxSimilarity < 1.0 ? sql`AND sim.similarity <= ${maxSimilarity}` : sql``}
          )
        ` : sql``}
        ${similarityClassification ? sql`
          INNER JOIN section_similarity_classifications cls ON (
            cls.jurisdiction = ${jurisdiction}
            AND cls.section_a = sim.section_a AND cls.section_b = sim.section_b
            AND cls.classification = ${similarityClassification}
          )
        ` : sql``}
        ${needsObligationsJoin ? sql`
          INNER JOIN obligations obl ON (
            obl.jurisdiction = ${jurisdiction}
            AND obl.section_id = s.id
            AND obl.category = ANY(${sql`ARRAY[${sql.join(obligationCategories!.map(c => sql`${c}`), sql`, `)}]::text[]`})
          )
        ` : sql``}
        ${needsImplementationJoin ? sql`
          INNER JOIN section_pahlka_implementations pi ON (
            pi.jurisdiction = ${jurisdiction}
            AND pi.section_id = s.id
            AND pi.has_implementation_issues = true
            ${implementationComplexity ? sql`AND pi.overall_complexity = ${implementationComplexity}` : sql``}
          )
        ` : sql``}
        ${needsAnachronismJoin ? sql`
          INNER JOIN section_anachronisms sa ON (
            sa.jurisdiction = ${jurisdiction}
            AND sa.section_id = s.id
            AND sa.has_anachronism = true
            ${anachronismSeverity ? sql`AND sa.overall_severity = ${anachronismSeverity}` : sql``}
          )
        ` : sql``}
        WHERE s.jurisdiction = ${jurisdiction}
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
        FROM sections s
        ${needsSimilarityJoin ? sql`
          INNER JOIN section_similarities sim ON (
            sim.jurisdiction = ${jurisdiction}
            AND (sim.section_a = s.id OR sim.section_b = s.id)
            ${minSimilarity > 0.7 ? sql`AND sim.similarity >= ${minSimilarity}` : sql``}
            ${maxSimilarity < 1.0 ? sql`AND sim.similarity <= ${maxSimilarity}` : sql``}
          )
        ` : sql``}
        ${similarityClassification ? sql`
          INNER JOIN section_similarity_classifications cls ON (
            cls.jurisdiction = ${jurisdiction}
            AND cls.section_a = sim.section_a AND cls.section_b = sim.section_b
            AND cls.classification = ${similarityClassification}
          )
        ` : sql``}
        ${needsObligationsJoin ? sql`
          INNER JOIN obligations obl ON (
            obl.jurisdiction = ${jurisdiction}
            AND obl.section_id = s.id
            AND obl.category = ANY(${sql`ARRAY[${sql.join(obligationCategories!.map(c => sql`${c}`), sql`, `)}]::text[]`})
          )
        ` : sql``}
        ${needsImplementationJoin ? sql`
          INNER JOIN section_pahlka_implementations pi ON (
            pi.jurisdiction = ${jurisdiction}
            AND pi.section_id = s.id
            AND pi.has_implementation_issues = true
            ${implementationComplexity ? sql`AND pi.overall_complexity = ${implementationComplexity}` : sql``}
          )
        ` : sql``}
        ${needsAnachronismJoin ? sql`
          INNER JOIN section_anachronisms sa ON (
            sa.jurisdiction = ${jurisdiction}
            AND sa.section_id = s.id
            AND sa.has_anachronism = true
            ${anachronismSeverity ? sql`AND sa.overall_severity = ${anachronismSeverity}` : sql``}
          )
        ` : sql``}
        WHERE s.jurisdiction = ${jurisdiction}
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
          obligationCategories: obligationCategories || null,
          hasImplementationIssues: hasImplementationIssues,
          implementationComplexity: implementationComplexity || null,
          hasAnachronisms: hasAnachronisms,
          anachronismSeverity: anachronismSeverity || null,
        },
      });
    } else {
      // Simple query without similarity joins
      const conditions: SQL[] = [
        eq(sections.jurisdiction, jurisdiction)
      ];

      // Add FTS condition if query provided
      if (query && query.trim()) {
        conditions.push(
          sql`text_fts @@ plainto_tsquery('english', ${query})`
        );
      }

      // Add title filter if provided
      if (title && title.trim()) {
        conditions.push(eq(sections.titleLabel, title));
      }

      // Add chapter filter if provided
      if (chapter && chapter.trim()) {
        conditions.push(eq(sections.chapterLabel, chapter));
      }

      // Add reporting filter if provided
      if (hasReporting) {
        conditions.push(eq(sections.hasReporting, true));
      }

      // If obligations filter is specified but no other joins, we need special handling
      if (needsObligationsJoin) {
        // Use subquery to filter sections that have obligations in the specified categories
        const baseSql = sql`
          SELECT DISTINCT
            s.id,
            s.citation,
            s.heading,
            LEFT(s.text_plain, 200) as snippet,
            s.title_label,
            s.chapter_label
          FROM sections s
          INNER JOIN obligations obl ON (
            obl.jurisdiction = ${jurisdiction}
            AND obl.section_id = s.id
            AND obl.category = ANY(${sql`ARRAY[${sql.join(obligationCategories!.map(c => sql`${c}`), sql`, `)}]::text[]`})
          )
          WHERE s.jurisdiction = ${jurisdiction}
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
          FROM sections s
          INNER JOIN obligations obl ON (
            obl.jurisdiction = ${jurisdiction}
            AND obl.section_id = s.id
            AND obl.category = ANY(${sql`ARRAY[${sql.join(obligationCategories!.map(c => sql`${c}`), sql`, `)}]::text[]`})
          )
          WHERE s.jurisdiction = ${jurisdiction}
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
            hasSimilar: false,
            minSimilarity: 0.7,
            maxSimilarity: 1.0,
            similarityClassification: null,
            obligationCategories: obligationCategories || null,
          },
        });
      }

      // Combine all conditions
      const whereClause = and(...conditions);

      // Get total count for pagination
      const [countResult] = await db
        .select({ count: sql<number>`count(*)::int` })
        .from(sections)
        .where(whereClause);

      const total = countResult?.count || 0;
      const totalPages = Math.ceil(total / limit);

      // Get paginated results
      const results = await db
        .select({
          id: sections.id,
          citation: sections.citation,
          heading: sections.heading,
          snippet: sql<string>`LEFT(${sections.textPlain}, 200)`,
          titleLabel: sections.titleLabel,
          chapterLabel: sections.chapterLabel,
        })
        .from(sections)
        .where(whereClause)
        .limit(limit)
        .offset(offset)
        .orderBy(sections.citation);

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
          obligationCategories: null,
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
