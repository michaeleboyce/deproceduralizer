import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { dcSections } from "@/db/schema";
import { sql } from "drizzle-orm";

/**
 * GET /api/filters/titles
 *
 * Returns list of distinct titles for filter dropdown
 */
export async function GET() {
  try {
    const titles = await db
      .selectDistinct({
        title: dcSections.titleLabel,
      })
      .from(dcSections)
      .orderBy(dcSections.titleLabel);

    return NextResponse.json({
      titles: titles.map((t) => t.title),
    });
  } catch (error) {
    console.error("Error fetching titles:", error);
    return NextResponse.json(
      { error: "Failed to fetch titles" },
      { status: 500 }
    );
  }
}
