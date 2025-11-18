import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sections } from "@/db/schema";
import { eq } from "drizzle-orm";

/**
 * GET /api/filters/titles
 *
 * Returns list of distinct titles for filter dropdown
 */
export async function GET() {
  try {
    // Hardcode jurisdiction to 'dc' for now (transparent to user)
    const jurisdiction = 'dc';

    const titles = await db
      .selectDistinct({
        title: sections.titleLabel,
      })
      .from(sections)
      .where(eq(sections.jurisdiction, jurisdiction))
      .orderBy(sections.titleLabel);

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
