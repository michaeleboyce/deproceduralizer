import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { obligations } from "@/db/schema";
import { sql, eq } from "drizzle-orm";

/**
 * GET /api/filters/obligations
 *
 * Returns list of unique obligation categories for the given jurisdiction
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const jurisdiction = searchParams.get("jurisdiction") || "dc";

    const result = await db
      .selectDistinct({ category: obligations.category })
      .from(obligations)
      .where(eq(obligations.jurisdiction, jurisdiction))
      .orderBy(obligations.category);

    const categories = result.map((row) => row.category);

    return NextResponse.json({ categories });
  } catch (error) {
    console.error("Failed to fetch obligation categories:", error);
    return NextResponse.json(
      { error: "Failed to fetch obligation categories" },
      { status: 500 }
    );
  }
}
