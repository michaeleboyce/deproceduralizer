import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { bookmarks } from '@/db/schema';
import { eq, and } from 'drizzle-orm';
import { getCurrentJurisdiction } from '@/lib/config';

/**
 * PATCH /api/bookmarks/[id]
 * Update bookmark note
 */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const jurisdiction = getCurrentJurisdiction();
  const bookmarkId = parseInt(id);

  if (isNaN(bookmarkId)) {
    return NextResponse.json({ error: 'Invalid bookmark ID' }, { status: 400 });
  }

  try {
    const body = await request.json();
    const { note } = body;

    // Update bookmark note
    const [updatedBookmark] = await db
      .update(bookmarks)
      .set({
        note: note || null,
        updatedAt: new Date(),
      })
      .where(and(
        eq(bookmarks.id, bookmarkId),
        eq(bookmarks.jurisdiction, jurisdiction)
      ))
      .returning();

    if (!updatedBookmark) {
      return NextResponse.json({ error: 'Bookmark not found' }, { status: 404 });
    }

    return NextResponse.json({ bookmark: updatedBookmark });
  } catch (error) {
    console.error('Error updating bookmark:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

/**
 * DELETE /api/bookmarks/[id]
 * Remove a bookmark
 */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const jurisdiction = getCurrentJurisdiction();
  const bookmarkId = parseInt(id);

  if (isNaN(bookmarkId)) {
    return NextResponse.json({ error: 'Invalid bookmark ID' }, { status: 400 });
  }

  try {
    const [deletedBookmark] = await db
      .delete(bookmarks)
      .where(and(
        eq(bookmarks.id, bookmarkId),
        eq(bookmarks.jurisdiction, jurisdiction)
      ))
      .returning();

    if (!deletedBookmark) {
      return NextResponse.json({ error: 'Bookmark not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, bookmark: deletedBookmark });
  } catch (error) {
    console.error('Error deleting bookmark:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
