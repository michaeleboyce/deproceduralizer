import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { sections } from "@/db/schema";
import { eq, and } from "drizzle-orm";

/**
 * GET handler for a single section by ID
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Hardcode jurisdiction to 'dc' for now (transparent to user)
    const jurisdiction = 'dc';

    const [section] = await db
      .select({
        id: sections.id,
        jurisdiction: sections.jurisdiction,
        citation: sections.citation,
        heading: sections.heading,
        textPlain: sections.textPlain,
        textHtml: sections.textHtml,
        titleLabel: sections.titleLabel,
        chapterLabel: sections.chapterLabel,
      })
      .from(sections)
      .where(and(
        eq(sections.jurisdiction, jurisdiction),
        eq(sections.id, id)
      ))
      .limit(1);

    if (!section) {
      return NextResponse.json(
        { error: "Section not found" },
        { status: 404 }
      );
    }

    return NextResponse.json(section);
  } catch (error) {
    console.error("Section fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch section" },
      { status: 500 }
    );
  }
}
