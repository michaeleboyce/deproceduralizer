import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { bookmarks } from '@/db/schema';
import { eq, and, desc } from 'drizzle-orm';
import { getCurrentJurisdiction, config } from '@/lib/config';

/**
 * GET /api/bookmarks
 * Fetch all bookmarks, optionally filtered by item type
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jurisdiction = getCurrentJurisdiction();

  const itemType = searchParams.get('itemType');
  const limitParam = parseInt(searchParams.get('limit') || '0');
  const limit = limitParam > 0 ? Math.min(limitParam, config.pagination.maxLimit) : config.pagination.maxLimit;
  const offset = parseInt(searchParams.get('offset') || '0');

  try {
    const whereConditions = [eq(bookmarks.jurisdiction, jurisdiction)];

    if (itemType) {
      whereConditions.push(eq(bookmarks.itemType, itemType));
    }

    const allBookmarks = await db
      .select()
      .from(bookmarks)
      .where(and(...whereConditions))
      .orderBy(desc(bookmarks.createdAt))
      .limit(limit)
      .offset(offset);

    return NextResponse.json({ bookmarks: allBookmarks });
  } catch (error) {
    console.error('Error fetching bookmarks:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

/**
 * POST /api/bookmarks
 * Create a new bookmark
 */
export async function POST(request: Request) {
  const jurisdiction = getCurrentJurisdiction();

  try {
    const body = await request.json();
    const { itemType, itemId, note } = body;

    // Validate required fields
    if (!itemType || !itemId) {
      return NextResponse.json(
        { error: 'itemType and itemId are required' },
        { status: 400 }
      );
    }

    // Validate item type
    const validItemTypes = ['section', 'conflict', 'duplicate', 'reporting', 'anachronism', 'implementation', 'implementation_indicator', 'anachronism_indicator'];
    if (!validItemTypes.includes(itemType)) {
      return NextResponse.json(
        { error: `Invalid itemType. Must be one of: ${validItemTypes.join(', ')}` },
        { status: 400 }
      );
    }

    // Insert bookmark (will fail if duplicate due to UNIQUE constraint)
    const [bookmark] = await db
      .insert(bookmarks)
      .values({
        jurisdiction,
        itemType,
        itemId,
        note: note || null,
      })
      .returning();

    return NextResponse.json({ bookmark }, { status: 201 });
  } catch (error: any) {
    // Check for unique constraint violation
    if (error.code === '23505') {
      return NextResponse.json(
        { error: 'This item is already bookmarked' },
        { status: 409 }
      );
    }

    console.error('Error creating bookmark:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
