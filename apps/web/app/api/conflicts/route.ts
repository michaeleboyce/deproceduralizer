import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { sectionSimilarityClassifications, sections } from '@/db/schema';
import { eq, and, desc, inArray, aliasedTable } from 'drizzle-orm';
import { getCurrentJurisdiction, config } from '@/lib/config';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const jurisdiction = getCurrentJurisdiction();

    const limitParam = parseInt(searchParams.get('limit') || '0');
    const limit = limitParam > 0 ? Math.min(limitParam, config.pagination.maxLimit) : config.pagination.defaultLimit;

    const offset = parseInt(searchParams.get('offset') || '0');
    const type = searchParams.get('type'); // 'conflicting' | 'duplicate' | 'all'

    const classificationTypes = type && type !== 'all'
        ? [type]
        : ['conflicting', 'duplicate'];

    const sectionsA = aliasedTable(sections, "sectionsA");
    const sectionsB = aliasedTable(sections, "sectionsB");

    try {
        // Fetch conflicting/duplicate classifications with joined section details
        const conflicts = await db
            .select({
                sectionA: sectionSimilarityClassifications.sectionA,
                sectionB: sectionSimilarityClassifications.sectionB,
                citationA: sectionsA.citation,
                headingA: sectionsA.heading,
                citationB: sectionsB.citation,
                headingB: sectionsB.heading,
                classification: sectionSimilarityClassifications.classification,
                explanation: sectionSimilarityClassifications.explanation,
                analyzedAt: sectionSimilarityClassifications.analyzedAt,
            })
            .from(sectionSimilarityClassifications)
            .innerJoin(sectionsA, and(
                eq(sectionsA.jurisdiction, sectionSimilarityClassifications.jurisdiction),
                eq(sectionsA.id, sectionSimilarityClassifications.sectionA)
            ))
            .innerJoin(sectionsB, and(
                eq(sectionsB.jurisdiction, sectionSimilarityClassifications.jurisdiction),
                eq(sectionsB.id, sectionSimilarityClassifications.sectionB)
            ))
            .where(and(
                eq(sectionSimilarityClassifications.jurisdiction, jurisdiction),
                inArray(sectionSimilarityClassifications.classification, classificationTypes)
            ))
            .orderBy(desc(sectionSimilarityClassifications.analyzedAt))
            .limit(limit)
            .offset(offset);

        return NextResponse.json({ conflicts });
    } catch (error) {
        console.error('Error fetching conflicts:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
