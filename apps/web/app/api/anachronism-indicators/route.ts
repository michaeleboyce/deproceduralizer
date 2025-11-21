import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import {
  anachronismIndicators,
  sectionAnachronisms,
  sections,
  sectionAnachronismHighlights,
} from '@/db/schema';
import { eq, and, desc, sql, or, like, inArray } from 'drizzle-orm';
import { getCurrentJurisdiction, config } from '@/lib/config';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jurisdiction = getCurrentJurisdiction();

  const limitParam = parseInt(searchParams.get('limit') || '0');
  const limit = limitParam > 0 ? Math.min(limitParam, config.pagination.maxLimit) : config.pagination.defaultLimit;
  const offset = parseInt(searchParams.get('offset') || '0');

  // Filters
  const severity = searchParams.get('severity');
  const category = searchParams.get('category');
  const title = searchParams.get('title');
  const chapter = searchParams.get('chapter');
  const requiresReview = searchParams.get('requiresReview') === 'true';
  const searchQuery = searchParams.get('searchQuery');
  const sortBy = searchParams.get('sortBy') || 'severity';

  try {
    // Build where conditions
    const whereConditions = [
      eq(anachronismIndicators.jurisdiction, jurisdiction),
    ];

    if (severity) {
      whereConditions.push(eq(anachronismIndicators.severity, severity));
    }

    if (category) {
      whereConditions.push(eq(anachronismIndicators.category, category));
    }

    if (title) {
      whereConditions.push(eq(sections.titleLabel, title));
    }

    if (chapter) {
      whereConditions.push(eq(sections.chapterLabel, chapter));
    }

    if (requiresReview) {
      whereConditions.push(eq(sectionAnachronisms.requiresImmediateReview, true));
    }

    if (searchQuery) {
      whereConditions.push(
        or(
          like(anachronismIndicators.explanation, `%${searchQuery}%`),
          like(sections.heading, `%${searchQuery}%`)
        )!
      );
    }

    // Determine sort order
    let orderByClause;
    switch (sortBy) {
      case 'severity':
        orderByClause = sql`CASE ${anachronismIndicators.severity}
          WHEN 'CRITICAL' THEN 1
          WHEN 'HIGH' THEN 2
          WHEN 'MEDIUM' THEN 3
          WHEN 'LOW' THEN 4
        END`;
        break;
      case 'category':
        orderByClause = anachronismIndicators.category;
        break;
      case 'citation':
        orderByClause = sections.citation;
        break;
      default:
        orderByClause = sql`CASE ${anachronismIndicators.severity}
          WHEN 'CRITICAL' THEN 1
          WHEN 'HIGH' THEN 2
          WHEN 'MEDIUM' THEN 3
          WHEN 'LOW' THEN 4
        END`;
    }

    // Fetch indicators with section context and parent analysis
    const indicatorsQuery = db
      .select({
        // Indicator fields
        id: anachronismIndicators.id,
        category: anachronismIndicators.category,
        severity: anachronismIndicators.severity,
        modernEquivalent: anachronismIndicators.modernEquivalent,
        recommendation: anachronismIndicators.recommendation,
        explanation: anachronismIndicators.explanation,
        // Section context
        sectionId: sections.id,
        citation: sections.citation,
        heading: sections.heading,
        titleLabel: sections.titleLabel,
        chapterLabel: sections.chapterLabel,
        // Parent analysis
        overallSeverity: sectionAnachronisms.overallSeverity,
        requiresImmediateReview: sectionAnachronisms.requiresImmediateReview,
        summary: sectionAnachronisms.summary,
        modelUsed: sectionAnachronisms.modelUsed,
      })
      .from(anachronismIndicators)
      .innerJoin(
        sectionAnachronisms,
        and(
          eq(anachronismIndicators.jurisdiction, sectionAnachronisms.jurisdiction),
          eq(anachronismIndicators.sectionId, sectionAnachronisms.sectionId)
        )
      )
      .innerJoin(
        sections,
        and(
          eq(anachronismIndicators.jurisdiction, sections.jurisdiction),
          eq(anachronismIndicators.sectionId, sections.id)
        )
      )
      .where(and(...whereConditions))
      .orderBy(orderByClause)
      .limit(limit)
      .offset(offset);

    const indicators = await indicatorsQuery;

    // Fetch matched phrases for each indicator
    const indicatorIds = indicators.map(i => i.id);
    const highlightsData = indicatorIds.length > 0
      ? await db
          .select({
            indicatorId: sectionAnachronismHighlights.indicatorId,
            phrase: sectionAnachronismHighlights.phrase,
          })
          .from(sectionAnachronismHighlights)
          .where(inArray(sectionAnachronismHighlights.indicatorId, indicatorIds))
      : [];

    // Group highlights by indicator ID
    const highlightsByIndicator = highlightsData.reduce((acc, h) => {
      if (!acc[h.indicatorId]) acc[h.indicatorId] = [];
      acc[h.indicatorId].push(h.phrase);
      return acc;
    }, {} as Record<number, string[]>);

    // Add matched phrases to indicators
    const results = indicators.map(indicator => ({
      ...indicator,
      matchedPhrases: highlightsByIndicator[indicator.id] || [],
    }));

    // Get total count for pagination
    const [{ count }] = await db
      .select({ count: sql<number>`count(*)` })
      .from(anachronismIndicators)
      .innerJoin(
        sectionAnachronisms,
        and(
          eq(anachronismIndicators.jurisdiction, sectionAnachronisms.jurisdiction),
          eq(anachronismIndicators.sectionId, sectionAnachronisms.sectionId)
        )
      )
      .innerJoin(
        sections,
        and(
          eq(anachronismIndicators.jurisdiction, sections.jurisdiction),
          eq(anachronismIndicators.sectionId, sections.id)
        )
      )
      .where(and(...whereConditions));

    // Get filter options
    const allCategories = await db
      .select({
        category: anachronismIndicators.category,
        count: sql<number>`count(*)`,
      })
      .from(anachronismIndicators)
      .where(eq(anachronismIndicators.jurisdiction, jurisdiction))
      .groupBy(anachronismIndicators.category)
      .orderBy(desc(sql`count(*)`));

    const severityDistribution = await db
      .select({
        severity: anachronismIndicators.severity,
        count: sql<number>`count(*)`,
      })
      .from(anachronismIndicators)
      .where(eq(anachronismIndicators.jurisdiction, jurisdiction))
      .groupBy(anachronismIndicators.severity);

    return NextResponse.json({
      results,
      total: count,
      filters: {
        severity,
        category,
        title,
        chapter,
        requiresReview,
        searchQuery,
        sortBy,
      },
      allCategories,
      severityDistribution,
    });
  } catch (error) {
    console.error('Error fetching anachronism indicators:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
