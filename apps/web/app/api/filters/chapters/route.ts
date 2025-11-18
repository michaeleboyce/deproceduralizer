import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { dcSections } from "@/db/schema";
import { eq } from "drizzle-orm";

/**
 * GET /api/filters/chapters?title=Title+1
 *
 * Returns list of distinct chapters, optionally filtered by title
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const title = searchParams.get("title");

    // Build query conditionally
    const query = db
      .selectDistinct({
        chapter: dcSections.chapterLabel,
      })
      .from(dcSections)
      .$dynamic();

    // Filter by title if provided
    if (title) {
      const chapters = await query
        .where(eq(dcSections.titleLabel, title))
        .orderBy(dcSections.chapterLabel);

      return NextResponse.json({
        chapters: chapters.map((c) => c.chapter),
      });
    }

    const chapters = await query.orderBy(dcSections.chapterLabel);

    return NextResponse.json({
      chapters: chapters.map((c) => c.chapter),
    });
  } catch (error) {
    console.error("Error fetching chapters:", error);
    return NextResponse.json(
      { error: "Failed to fetch chapters" },
      { status: 500 }
    );
  }
}
