import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sections } from "@/db/schema";
import { eq, and } from "drizzle-orm";

/**
 * GET /api/filters/chapters?title=Title+1
 *
 * Returns list of distinct chapters, optionally filtered by title
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const title = searchParams.get("title");

    // Hardcode jurisdiction to 'dc' for now (transparent to user)
    const jurisdiction = 'dc';

    // Build query conditionally
    const query = db
      .selectDistinct({
        chapter: sections.chapterLabel,
      })
      .from(sections)
      .$dynamic();

    // Filter by title if provided, always filter by jurisdiction
    if (title) {
      const chapters = await query
        .where(and(
          eq(sections.jurisdiction, jurisdiction),
          eq(sections.titleLabel, title)
        ))
        .orderBy(sections.chapterLabel);

      return NextResponse.json({
        chapters: chapters.map((c) => c.chapter),
      });
    }

    const chapters = await query
      .where(eq(sections.jurisdiction, jurisdiction))
      .orderBy(sections.chapterLabel);

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
