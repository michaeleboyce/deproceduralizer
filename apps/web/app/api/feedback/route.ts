import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { indicatorFeedback } from "@/db/schema";
import { eq, and, sql } from "drizzle-orm";

/**
 * GET handler for retrieving feedback
 * Query params:
 * - itemType: Type of item (anachronism_indicator, implementation_indicator, similarity_classification)
 * - itemId: ID of the item
 * - jurisdiction: Jurisdiction (default: dc)
 * - reviewerId: Optional filter by reviewer
 * - rating: Optional filter by rating
 * - includeContext: Optional flag to include section_id for navigation (default: false)
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const itemType = searchParams.get("itemType");
    const itemId = searchParams.get("itemId");
    const jurisdiction = searchParams.get("jurisdiction") || "dc";
    const reviewerId = searchParams.get("reviewerId");
    const rating = searchParams.get("rating");
    const includeContext = searchParams.get("includeContext") === "true";

    // Build query conditions
    const conditions = [];

    if (itemType && itemId) {
      // Get feedback for a specific item
      conditions.push(eq(indicatorFeedback.itemType, itemType));
      conditions.push(eq(indicatorFeedback.itemId, Number(itemId)));
      conditions.push(eq(indicatorFeedback.jurisdiction, jurisdiction));
    } else if (reviewerId) {
      // Get all feedback by reviewer
      conditions.push(eq(indicatorFeedback.reviewerId, reviewerId));
      conditions.push(eq(indicatorFeedback.jurisdiction, jurisdiction));
    } else if (itemType) {
      // Get all feedback for an item type
      conditions.push(eq(indicatorFeedback.itemType, itemType));
      conditions.push(eq(indicatorFeedback.jurisdiction, jurisdiction));
    } else {
      // Get all feedback for jurisdiction
      conditions.push(eq(indicatorFeedback.jurisdiction, jurisdiction));
    }

    // Add rating filter if provided
    if (rating) {
      conditions.push(eq(indicatorFeedback.rating, rating));
    }

    const feedback = await db
      .select()
      .from(indicatorFeedback)
      .where(and(...conditions))
      .orderBy(sql`${indicatorFeedback.reviewedAt} DESC`);

    // Convert BigInt to string for JSON serialization and optionally add section context
    const serializedFeedback = await Promise.all(
      feedback.map(async (f) => {
        const base = {
          ...f,
          id: f.id.toString(),
          itemId: f.itemId.toString(),
        };

        if (!includeContext) {
          return base;
        }

        // Add section_id based on item type
        let sectionId = null;

        if (f.itemType === "anachronism_indicator") {
          // Query anachronism_indicators to get section_id
          const result = await db.execute(
            sql`SELECT section_id FROM anachronism_indicators WHERE id = ${f.itemId}`
          );
          sectionId = result.rows[0]?.section_id || null;
        } else if (f.itemType === "implementation_indicator") {
          // Query pahlka_implementation_indicators to get section_id
          const result = await db.execute(
            sql`SELECT section_id FROM pahlka_implementation_indicators WHERE id = ${f.itemId}`
          );
          sectionId = result.rows[0]?.section_id || null;
        } else if (f.itemType === "similarity_classification") {
          // Parse itemId which is formatted as "sectionA:sectionB"
          const parts = f.itemId.toString().split(":");
          sectionId = parts[0] || null;
        }

        return {
          ...base,
          sectionId,
        };
      })
    );

    return NextResponse.json({
      feedback: serializedFeedback,
      count: serializedFeedback.length,
    });
  } catch (error) {
    console.error("Error fetching feedback:", error);
    return NextResponse.json(
      { error: "Failed to fetch feedback" },
      { status: 500 }
    );
  }
}

/**
 * POST handler for creating or updating feedback
 * Body should contain:
 * - itemType: Type of item
 * - itemId: ID of the item
 * - jurisdiction: Jurisdiction (default: dc)
 * - reviewerId: Reviewer identifier (required)
 * - reviewerName: Reviewer display name
 * - rating: Feedback rating (required)
 * - comment: Required explanation
 * - suggestedCategory: Optional correction
 * - suggestedSeverity: Optional correction
 * - suggestedComplexity: Optional correction
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    if (!body.itemType || !body.itemId || !body.reviewerId || !body.rating || !body.comment) {
      return NextResponse.json(
        {
          error: "Missing required fields: itemType, itemId, reviewerId, rating, comment",
        },
        { status: 400 }
      );
    }

    // Validate rating
    const validRatings = [
      "correct",
      "false_positive",
      "wrong_category",
      "wrong_severity",
      "missing_context",
      "needs_refinement",
    ];
    if (!validRatings.includes(body.rating)) {
      return NextResponse.json(
        { error: `Invalid rating. Must be one of: ${validRatings.join(", ")}` },
        { status: 400 }
      );
    }

    // Validate comment is not empty
    if (!body.comment.trim()) {
      return NextResponse.json(
        { error: "Comment cannot be empty" },
        { status: 400 }
      );
    }

    const jurisdiction = body.jurisdiction || "dc";

    // Check if feedback already exists for this reviewer/item combination
    const existingFeedback = await db
      .select()
      .from(indicatorFeedback)
      .where(
        and(
          eq(indicatorFeedback.itemType, body.itemType),
          eq(indicatorFeedback.itemId, Number(body.itemId)),
          eq(indicatorFeedback.reviewerId, body.reviewerId),
          eq(indicatorFeedback.jurisdiction, jurisdiction)
        )
      );

    let result;

    if (existingFeedback.length > 0) {
      // Update existing feedback
      result = await db
        .update(indicatorFeedback)
        .set({
          rating: body.rating,
          comment: body.comment,
          suggestedCategory: body.suggestedCategory || null,
          suggestedSeverity: body.suggestedSeverity || null,
          suggestedComplexity: body.suggestedComplexity || null,
          reviewerName: body.reviewerName || null,
          reviewedAt: sql`NOW()`,
          updatedAt: sql`NOW()`,
        })
        .where(eq(indicatorFeedback.id, existingFeedback[0].id))
        .returning();
    } else {
      // Insert new feedback
      result = await db
        .insert(indicatorFeedback)
        .values({
          itemType: body.itemType,
          itemId: Number(body.itemId),
          jurisdiction,
          reviewerId: body.reviewerId,
          reviewerName: body.reviewerName || null,
          rating: body.rating,
          comment: body.comment,
          suggestedCategory: body.suggestedCategory || null,
          suggestedSeverity: body.suggestedSeverity || null,
          suggestedComplexity: body.suggestedComplexity || null,
        })
        .returning();
    }

    // Serialize BigInt for JSON
    const serializedResult = {
      ...result[0],
      id: result[0].id.toString(),
      itemId: result[0].itemId.toString(),
    };

    return NextResponse.json({
      success: true,
      feedback: serializedResult,
    });
  } catch (error) {
    console.error("Error saving feedback:", error);
    return NextResponse.json(
      { error: "Failed to save feedback" },
      { status: 500 }
    );
  }
}

/**
 * DELETE handler for removing feedback
 * Query params:
 * - id: Feedback ID to delete
 */
export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json(
        { error: "Missing required parameter: id" },
        { status: 400 }
      );
    }

    await db
      .delete(indicatorFeedback)
      .where(eq(indicatorFeedback.id, Number(id)));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting feedback:", error);
    return NextResponse.json(
      { error: "Failed to delete feedback" },
      { status: 500 }
    );
  }
}
