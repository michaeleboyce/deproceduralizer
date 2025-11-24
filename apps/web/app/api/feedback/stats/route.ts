import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { indicatorFeedback } from "@/db/schema";
import { eq, sql } from "drizzle-orm";
import { validateJurisdiction } from "@/lib/config";

/**
 * GET handler for feedback statistics
 * Query params:
 * - jurisdiction: Jurisdiction (default: dc)
 * - itemType: Optional filter by item type
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const jurisdiction = validateJurisdiction(searchParams.get("jurisdiction"));
    const itemType = searchParams.get("itemType");

    // Build WHERE clause
    const whereConditions = itemType
      ? sql`WHERE jurisdiction = ${jurisdiction} AND item_type = ${itemType}`
      : sql`WHERE jurisdiction = ${jurisdiction}`;

    // Get rating distribution
    const ratingStats = await db.execute(sql`
      SELECT
        rating,
        COUNT(*) as count,
        COUNT(DISTINCT reviewer_id) as reviewer_count
      FROM indicator_feedback
      ${whereConditions}
      GROUP BY rating
      ORDER BY count DESC
    `);

    // Get item type distribution
    const itemTypeStats = await db.execute(sql`
      SELECT
        item_type,
        COUNT(*) as count,
        COUNT(DISTINCT reviewer_id) as reviewer_count
      FROM indicator_feedback
      ${whereConditions}
      GROUP BY item_type
      ORDER BY count DESC
    `);

    // Get reviewer statistics
    const reviewerStats = await db.execute(sql`
      SELECT
        reviewer_id,
        reviewer_name,
        COUNT(*) as review_count,
        COUNT(DISTINCT item_type) as item_types_reviewed
      FROM indicator_feedback
      ${whereConditions}
      GROUP BY reviewer_id, reviewer_name
      ORDER BY review_count DESC
    `);

    // Get total counts
    const totals = await db.execute(sql`
      SELECT
        COUNT(*) as total_reviews,
        COUNT(DISTINCT reviewer_id) as total_reviewers,
        COUNT(DISTINCT item_id) as total_items_reviewed,
        MIN(reviewed_at) as first_review_date,
        MAX(reviewed_at) as last_review_date
      FROM indicator_feedback
      ${whereConditions}
    `);

    // Get false positive rate
    const falsePositiveRate = await db.execute(sql`
      SELECT
        COUNT(*) FILTER (WHERE rating = 'false_positive') as false_positives,
        COUNT(*) as total,
        ROUND(
          CAST((COUNT(*) FILTER (WHERE rating = 'false_positive')::float / NULLIF(COUNT(*), 0)) * 100 AS numeric),
          2
        ) as false_positive_percentage
      FROM indicator_feedback
      ${whereConditions}
    `);

    // Handle empty results with defaults
    const totalsData = totals.rows[0] || {
      total_reviews: '0',
      total_reviewers: '0',
      total_items_reviewed: '0',
      first_review_date: null,
      last_review_date: null,
    };

    const falsePositiveData = falsePositiveRate.rows[0] || {
      false_positives: '0',
      total: '0',
      false_positive_percentage: '0',
    };

    return NextResponse.json({
      ratingDistribution: ratingStats.rows || [],
      itemTypeDistribution: itemTypeStats.rows || [],
      reviewerStatistics: reviewerStats.rows || [],
      totals: totalsData,
      falsePositiveRate: falsePositiveData,
    });
  } catch (error) {
    console.error("Error fetching feedback stats:", error);
    return NextResponse.json(
      { error: "Failed to fetch feedback statistics" },
      { status: 500 }
    );
  }
}
