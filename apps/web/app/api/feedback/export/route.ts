import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { indicatorFeedback } from "@/db/schema";
import { eq, and, sql } from "drizzle-orm";

/**
 * GET handler for exporting feedback data
 * Query params:
 * - format: Export format (json or csv) (default: json)
 * - jurisdiction: Jurisdiction (default: dc)
 * - itemType: Optional filter by item type
 * - rating: Optional filter by rating
 * - reviewerId: Optional filter by reviewer
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const format = searchParams.get("format") || "json";
    const jurisdiction = searchParams.get("jurisdiction") || "dc";
    const itemType = searchParams.get("itemType");
    const rating = searchParams.get("rating");
    const reviewerId = searchParams.get("reviewerId");

    // Build query conditions
    const conditions = [eq(indicatorFeedback.jurisdiction, jurisdiction)];

    if (itemType) {
      conditions.push(eq(indicatorFeedback.itemType, itemType));
    }
    if (rating) {
      conditions.push(eq(indicatorFeedback.rating, rating));
    }
    if (reviewerId) {
      conditions.push(eq(indicatorFeedback.reviewerId, reviewerId));
    }

    const feedback = await db
      .select()
      .from(indicatorFeedback)
      .where(and(...conditions))
      .orderBy(sql`${indicatorFeedback.reviewedAt} DESC`);

    // Convert BigInt to string for serialization
    const serializedFeedback = feedback.map((f) => ({
      id: f.id.toString(),
      item_type: f.itemType,
      item_id: f.itemId.toString(),
      jurisdiction: f.jurisdiction,
      reviewer_id: f.reviewerId,
      reviewer_name: f.reviewerName || "",
      rating: f.rating,
      comment: f.comment,
      suggested_category: f.suggestedCategory || "",
      suggested_severity: f.suggestedSeverity || "",
      suggested_complexity: f.suggestedComplexity || "",
      reviewed_at: f.reviewedAt.toISOString(),
      created_at: f.createdAt.toISOString(),
      updated_at: f.updatedAt.toISOString(),
    }));

    if (format === "csv") {
      // Generate CSV
      const headers = [
        "id",
        "item_type",
        "item_id",
        "jurisdiction",
        "reviewer_id",
        "reviewer_name",
        "rating",
        "comment",
        "suggested_category",
        "suggested_severity",
        "suggested_complexity",
        "reviewed_at",
        "created_at",
        "updated_at",
      ];

      const csvRows = [
        headers.join(","),
        ...serializedFeedback.map((row) =>
          headers
            .map((header) => {
              const value = row[header as keyof typeof row];
              // Escape quotes and wrap in quotes if contains comma, quote, or newline
              const stringValue = String(value || "");
              if (
                stringValue.includes(",") ||
                stringValue.includes('"') ||
                stringValue.includes("\n")
              ) {
                return `"${stringValue.replace(/"/g, '""')}"`;
              }
              return stringValue;
            })
            .join(",")
        ),
      ];

      const csvContent = csvRows.join("\n");

      return new NextResponse(csvContent, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": `attachment; filename="feedback-export-${jurisdiction}-${new Date().toISOString().split("T")[0]}.csv"`,
        },
      });
    } else {
      // Return JSON
      return new NextResponse(JSON.stringify(serializedFeedback, null, 2), {
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": `attachment; filename="feedback-export-${jurisdiction}-${new Date().toISOString().split("T")[0]}.json"`,
        },
      });
    }
  } catch (error) {
    console.error("Error exporting feedback:", error);
    return NextResponse.json(
      { error: "Failed to export feedback" },
      { status: 500 }
    );
  }
}
