import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import {
  pahlkaImplementationIndicators,
  sectionPahlkaImplementations,
  sections,
  sectionPahlkaHighlights,
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
  const complexity = searchParams.get('complexity');
  const category = searchParams.get('category');
  const title = searchParams.get('title');
  const chapter = searchParams.get('chapter');
  const requiresTechnicalReview = searchParams.get('requiresTechnicalReview') === 'true';
  const searchQuery = searchParams.get('searchQuery');
  const sortBy = searchParams.get('sortBy') || 'complexity';

  try {
    // Build where conditions
    const whereConditions = [
      eq(pahlkaImplementationIndicators.jurisdiction, jurisdiction),
    ];

    if (complexity) {
      whereConditions.push(eq(pahlkaImplementationIndicators.complexity, complexity));
    }

    if (category) {
      whereConditions.push(eq(pahlkaImplementationIndicators.category, category));
    }

    if (title) {
      whereConditions.push(eq(sections.titleLabel, title));
    }

    if (chapter) {
      whereConditions.push(eq(sections.chapterLabel, chapter));
    }

    if (requiresTechnicalReview) {
      whereConditions.push(eq(sectionPahlkaImplementations.requiresTechnicalReview, true));
    }

    if (searchQuery) {
      whereConditions.push(
        or(
          like(pahlkaImplementationIndicators.explanation, `%${searchQuery}%`),
          like(pahlkaImplementationIndicators.implementationApproach, `%${searchQuery}%`),
          like(sections.heading, `%${searchQuery}%`)
        )!
      );
    }

    // Determine sort order
    let orderByClause;
    switch (sortBy) {
      case 'complexity':
        orderByClause = sql`CASE ${pahlkaImplementationIndicators.complexity}
          WHEN 'HIGH' THEN 1
          WHEN 'MEDIUM' THEN 2
          WHEN 'LOW' THEN 3
        END`;
        break;
      case 'category':
        orderByClause = pahlkaImplementationIndicators.category;
        break;
      case 'citation':
        orderByClause = sections.citation;
        break;
      default:
        orderByClause = sql`CASE ${pahlkaImplementationIndicators.complexity}
          WHEN 'HIGH' THEN 1
          WHEN 'MEDIUM' THEN 2
          WHEN 'LOW' THEN 3
        END`;
    }

    // Fetch indicators with section context and parent analysis
    const indicatorsQuery = db
      .select({
        // Indicator fields
        id: pahlkaImplementationIndicators.id,
        category: pahlkaImplementationIndicators.category,
        complexity: pahlkaImplementationIndicators.complexity,
        implementationApproach: pahlkaImplementationIndicators.implementationApproach,
        effortEstimate: pahlkaImplementationIndicators.effortEstimate,
        explanation: pahlkaImplementationIndicators.explanation,
        // Section context
        sectionId: sections.id,
        citation: sections.citation,
        heading: sections.heading,
        titleLabel: sections.titleLabel,
        chapterLabel: sections.chapterLabel,
        // Parent analysis
        overallComplexity: sectionPahlkaImplementations.overallComplexity,
        requiresTechnicalReview: sectionPahlkaImplementations.requiresTechnicalReview,
        summary: sectionPahlkaImplementations.summary,
        modelUsed: sectionPahlkaImplementations.modelUsed,
      })
      .from(pahlkaImplementationIndicators)
      .innerJoin(
        sectionPahlkaImplementations,
        and(
          eq(pahlkaImplementationIndicators.jurisdiction, sectionPahlkaImplementations.jurisdiction),
          eq(pahlkaImplementationIndicators.sectionId, sectionPahlkaImplementations.sectionId)
        )
      )
      .innerJoin(
        sections,
        and(
          eq(pahlkaImplementationIndicators.jurisdiction, sections.jurisdiction),
          eq(pahlkaImplementationIndicators.sectionId, sections.id)
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
            indicatorId: sectionPahlkaHighlights.indicatorId,
            phrase: sectionPahlkaHighlights.phrase,
          })
          .from(sectionPahlkaHighlights)
          .where(inArray(sectionPahlkaHighlights.indicatorId, indicatorIds))
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
      .from(pahlkaImplementationIndicators)
      .innerJoin(
        sectionPahlkaImplementations,
        and(
          eq(pahlkaImplementationIndicators.jurisdiction, sectionPahlkaImplementations.jurisdiction),
          eq(pahlkaImplementationIndicators.sectionId, sectionPahlkaImplementations.sectionId)
        )
      )
      .innerJoin(
        sections,
        and(
          eq(pahlkaImplementationIndicators.jurisdiction, sections.jurisdiction),
          eq(pahlkaImplementationIndicators.sectionId, sections.id)
        )
      )
      .where(and(...whereConditions));

    // Get filter options
    const allCategories = await db
      .select({
        category: pahlkaImplementationIndicators.category,
        count: sql<number>`count(*)`,
      })
      .from(pahlkaImplementationIndicators)
      .where(eq(pahlkaImplementationIndicators.jurisdiction, jurisdiction))
      .groupBy(pahlkaImplementationIndicators.category)
      .orderBy(desc(sql`count(*)`));

    const complexityDistribution = await db
      .select({
        complexity: pahlkaImplementationIndicators.complexity,
        count: sql<number>`count(*)`,
      })
      .from(pahlkaImplementationIndicators)
      .where(eq(pahlkaImplementationIndicators.jurisdiction, jurisdiction))
      .groupBy(pahlkaImplementationIndicators.complexity);

    return NextResponse.json({
      results,
      total: count,
      filters: {
        complexity,
        category,
        title,
        chapter,
        requiresTechnicalReview,
        searchQuery,
        sortBy,
      },
      allCategories,
      complexityDistribution,
    });
  } catch (error) {
    console.error('Error fetching implementation indicators:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
