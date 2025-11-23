import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import {
  anachronismIndicators,
  pahlkaImplementationIndicators,
  sectionSimilarityClassifications,
  sections,
  indicatorFeedback,
} from "@/db/schema";
import { eq, sql, and, notInArray } from "drizzle-orm";

/**
 * GET handler for unreviewed items queue
 * Query params:
 * - jurisdiction: Jurisdiction (default: dc)
 * - itemType: Filter by item type (anachronism_indicator, implementation_indicator, similarity_classification, all)
 * - limit: Number of items to return (default: 50)
 * - offset: Pagination offset (default: 0)
 * - sortBy: Sort criteria (severity, complexity, citation) (default: severity)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const jurisdiction = searchParams.get("jurisdiction") || "dc";
    const itemType = searchParams.get("itemType") || "all";
    const limit = parseInt(searchParams.get("limit") || "50");
    const offset = parseInt(searchParams.get("offset") || "0");
    const sortBy = searchParams.get("sortBy") || "severity";

    const results: any[] = [];

    // Helper function to get reviewed item IDs for a type
    const getReviewedIds = async (type: string) => {
      const reviewed = await db
        .select({ itemId: indicatorFeedback.itemId })
        .from(indicatorFeedback)
        .where(
          and(
            eq(indicatorFeedback.itemType, type),
            eq(indicatorFeedback.jurisdiction, jurisdiction)
          )
        );
      return reviewed.map((r) => r.itemId);
    };

    // Fetch unreviewed anachronism indicators
    if (itemType === "all" || itemType === "anachronism_indicator") {
      const reviewedIds = await getReviewedIds("anachronism_indicator");

      let query = db
        .select({
          id: anachronismIndicators.id,
          itemType: sql<string>`'anachronism_indicator'`,
          category: anachronismIndicators.category,
          severity: anachronismIndicators.severity,
          explanation: anachronismIndicators.explanation,
          recommendation: anachronismIndicators.recommendation,
          modernEquivalent: anachronismIndicators.modernEquivalent,
          sectionId: anachronismIndicators.sectionId,
          citation: sections.citation,
          heading: sections.heading,
          titleLabel: sections.titleLabel,
          chapterLabel: sections.chapterLabel,
        })
        .from(anachronismIndicators)
        .innerJoin(
          sections,
          and(
            eq(anachronismIndicators.sectionId, sections.id),
            eq(anachronismIndicators.jurisdiction, sections.jurisdiction)
          )
        )
        .where(eq(anachronismIndicators.jurisdiction, jurisdiction));

      if (reviewedIds.length > 0) {
        query = query.where(notInArray(anachronismIndicators.id, reviewedIds));
      }

      // Apply sorting
      if (sortBy === "severity") {
        query = query.orderBy(
          sql`CASE ${anachronismIndicators.severity}
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4
            ELSE 5 END`
        );
      } else if (sortBy === "citation") {
        query = query.orderBy(sections.citation);
      }

      const anachronisms = await query.limit(limit).offset(offset);
      results.push(...anachronisms);
    }

    // Fetch unreviewed implementation indicators
    if (itemType === "all" || itemType === "implementation_indicator") {
      const reviewedIds = await getReviewedIds("implementation_indicator");

      let query = db
        .select({
          id: pahlkaImplementationIndicators.id,
          itemType: sql<string>`'implementation_indicator'`,
          category: pahlkaImplementationIndicators.category,
          complexity: pahlkaImplementationIndicators.complexity,
          explanation: pahlkaImplementationIndicators.explanation,
          implementationApproach: pahlkaImplementationIndicators.implementationApproach,
          effortEstimate: pahlkaImplementationIndicators.effortEstimate,
          sectionId: pahlkaImplementationIndicators.sectionId,
          citation: sections.citation,
          heading: sections.heading,
          titleLabel: sections.titleLabel,
          chapterLabel: sections.chapterLabel,
        })
        .from(pahlkaImplementationIndicators)
        .innerJoin(
          sections,
          and(
            eq(pahlkaImplementationIndicators.sectionId, sections.id),
            eq(pahlkaImplementationIndicators.jurisdiction, sections.jurisdiction)
          )
        )
        .where(eq(pahlkaImplementationIndicators.jurisdiction, jurisdiction));

      if (reviewedIds.length > 0) {
        query = query.where(
          notInArray(pahlkaImplementationIndicators.id, reviewedIds)
        );
      }

      // Apply sorting
      if (sortBy === "complexity") {
        query = query.orderBy(
          sql`CASE ${pahlkaImplementationIndicators.complexity}
            WHEN 'HIGH' THEN 1
            WHEN 'MEDIUM' THEN 2
            WHEN 'LOW' THEN 3
            ELSE 4 END`
        );
      } else if (sortBy === "citation") {
        query = query.orderBy(sections.citation);
      }

      const implementations = await query.limit(limit).offset(offset);
      results.push(...implementations);
    }

    // Fetch unreviewed similarity classifications (conflicts/duplicates)
    if (itemType === "all" || itemType === "similarity_classification") {
      const reviewedIds = await getReviewedIds("similarity_classification");

      // For similarity classifications, we need to create a composite key
      // Since we can't filter by composite key easily, we'll fetch all and filter in memory
      const allClassifications = await db
        .select({
          sectionA: sectionSimilarityClassifications.sectionA,
          sectionB: sectionSimilarityClassifications.sectionB,
          classification: sectionSimilarityClassifications.classification,
          explanation: sectionSimilarityClassifications.explanation,
          modelUsed: sectionSimilarityClassifications.modelUsed,
          analyzedAt: sectionSimilarityClassifications.analyzedAt,
        })
        .from(sectionSimilarityClassifications)
        .where(eq(sectionSimilarityClassifications.jurisdiction, jurisdiction))
        .limit(limit)
        .offset(offset);

      // Note: For similarity classifications, itemId would need to be a composite key
      // This is simplified for now - in practice, you might want to create a surrogate key
      results.push(
        ...allClassifications.map((c) => ({
          itemType: "similarity_classification",
          ...c,
        }))
      );
    }

    // Get total count of unreviewed items
    const totalUnreviewedQuery = await db.execute(sql`
      SELECT
        (SELECT COUNT(*) FROM anachronism_indicators
         WHERE jurisdiction = ${jurisdiction}
         AND id NOT IN (SELECT item_id FROM indicator_feedback
                        WHERE item_type = 'anachronism_indicator'
                        AND jurisdiction = ${jurisdiction})) as anachronism_count,
        (SELECT COUNT(*) FROM pahlka_implementation_indicators
         WHERE jurisdiction = ${jurisdiction}
         AND id NOT IN (SELECT item_id FROM indicator_feedback
                        WHERE item_type = 'implementation_indicator'
                        AND jurisdiction = ${jurisdiction})) as implementation_count,
        (SELECT COUNT(*) FROM section_similarity_classifications
         WHERE jurisdiction = ${jurisdiction}) as similarity_count
    `);

    const counts = totalUnreviewedQuery.rows[0] as any;

    return NextResponse.json({
      items: results,
      pagination: {
        limit,
        offset,
        totalUnreviewed: {
          anachronisms: parseInt(counts.anachronism_count || "0"),
          implementations: parseInt(counts.implementation_count || "0"),
          similarities: parseInt(counts.similarity_count || "0"),
          total:
            parseInt(counts.anachronism_count || "0") +
            parseInt(counts.implementation_count || "0") +
            parseInt(counts.similarity_count || "0"),
        },
      },
    });
  } catch (error) {
    console.error("Error fetching review queue:", error);
    return NextResponse.json(
      { error: "Failed to fetch review queue" },
      { status: 500 }
    );
  }
}
