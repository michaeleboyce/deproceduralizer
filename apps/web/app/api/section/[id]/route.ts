import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { dcSections } from "@/db/schema";
import { eq } from "drizzle-orm";

/**
 * GET handler for a single section by ID
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const [section] = await db
      .select({
        id: dcSections.id,
        citation: dcSections.citation,
        heading: dcSections.heading,
        textPlain: dcSections.textPlain,
        textHtml: dcSections.textHtml,
        titleLabel: dcSections.titleLabel,
        chapterLabel: dcSections.chapterLabel,
      })
      .from(dcSections)
      .where(eq(dcSections.id, id))
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
